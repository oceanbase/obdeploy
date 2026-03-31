# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import, division, print_function
import os
import subprocess

def gen_ca(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    server_config = cluster_config.get_server_conf_with_default(cluster_config.servers[0])
    
    if not server_config.get('enable_rpc_service'):
        return plugin_context.return_true()
        
    current_name = cluster_config.deploy_name
    work_dir = '/tmp/.seekdb_ca'
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    stdio.start_loading("generating CA for %s" % current_name)
        
    ca_key = os.path.join(work_dir, 'ca.key')
    ca_cert = os.path.join(work_dir, 'ca.pem')

    def _run_openssl(cmd, cwd_path):
        import subprocess
        env = os.environ.copy()
        # Clean environment variables that cause openssl to fail across OS versions
        env.pop('LD_LIBRARY_PATH', None)
        env.pop('OPENSSL_CONF', None)
        
        # Use system openssl if exists to avoid conda openssl issues
        openssl_bin = 'openssl'
        if os.path.exists('/usr/bin/openssl'):
            openssl_bin = '/usr/bin/openssl'
            
        if cmd.startswith('openssl '):
            cmd = openssl_bin + cmd[7:]
            
        try:
            p = subprocess.Popen(cmd, shell=True, cwd=cwd_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            out, err = p.communicate()
            if p.returncode != 0:
                err_msg = err.decode('utf-8') if err else 'Unknown error'
                raise RuntimeError("Command '{}' failed with exit status {}.\nError details: {}".format(cmd, p.returncode, err_msg))
        except Exception as e:
            raise RuntimeError("Execute command failed: {}".format(str(e)))

    # Check if CA exists
    if not os.path.exists(ca_cert):
        stdio.verbose('Generating Root CA...')
        _run_openssl('openssl genrsa -out ca.key 4096', work_dir)
        _run_openssl('openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -subj "/C=CN/O=OceanBase/CN=OceanBase-CA" -out ca.pem', work_dir)
    else:
        stdio.verbose('Root CA already exists.')

    def generate_and_distribute(server, client, cluster_conf, cluster_name):
        ip = server.ip
        # Determine role just for file naming (purely cosmetic here, can just use cluster_name)
        role = cluster_name
        key_name = '{}_key.pem'.format(role)
        csr_name = '{}.csr'.format(role)
        san_name = '{}_san.ext'.format(role)
        cert_name = '{}_cert.pem'.format(role)
        
        cluster_work_dir = os.path.join(work_dir, cluster_name)
        if not os.path.exists(cluster_work_dir):
            os.makedirs(cluster_work_dir)
            
        local_key = os.path.join(cluster_work_dir, key_name)
        local_san = os.path.join(cluster_work_dir, san_name)
        local_cert = os.path.join(cluster_work_dir, cert_name)
            
        server_config = cluster_conf.get_server_conf(server)
        home_path = server_config['home_path']
        wallet_dir = os.path.join(home_path, 'wallet')

        if not client.execute_command('ls %s' % (os.path.join(wallet_dir, 'cert.pem'))):
            stdio.verbose('Generating certificate for {} in {}'.format(ip, cluster_name))
            
            _run_openssl('openssl genrsa -out {} 2048'.format(key_name), cluster_work_dir)
            _run_openssl('openssl req -new -key {} -subj "/C=CN/O=OceanBase/CN={}" -out {}'.format(key_name, ip, csr_name), cluster_work_dir)
            
            with open(local_san, 'w') as f:
                f.write("subjectAltName=IP:{}".format(ip))
                
            _run_openssl('openssl x509 -req -in {} -CA {} -CAkey {} -CAcreateserial -extfile {} -days 3650 -sha256 -out {}'.format(csr_name, ca_cert, ca_key, san_name, cert_name), cluster_work_dir)
            
            stdio.verbose('Distributing certificates to {}...'.format(ip))
            
            if not client.execute_command('mkdir -p {}'.format(wallet_dir)):
                stdio.error('Failed to create wallet directory on {}'.format(ip))
                return False

            if not client.put_file(ca_cert, os.path.join(wallet_dir, 'ca.pem')):
                stdio.error('Failed to copy ca.pem to {}'.format(ip))
                return False
                
            if not client.put_file(local_key, os.path.join(wallet_dir, 'key.pem')):
                stdio.error('Failed to copy key.pem to {}'.format(ip))
                return False

            if not client.put_file(local_cert, os.path.join(wallet_dir, 'cert.pem')):
                stdio.error('Failed to copy cert.pem to {}'.format(ip))
                return False
            
            client.execute_command('chmod 600 {}'.format(os.path.join(wallet_dir, 'key.pem')))
            client.execute_command('chmod 644 {}'.format(os.path.join(wallet_dir, 'cert.pem')))
            client.execute_command('chmod 644 {}'.format(os.path.join(wallet_dir, 'ca.pem')))
        else:
            stdio.verbose("The certificate for %s under %s already exists." % (cluster_name, ip))
            
        return True

    # Retrieve clients for the current cluster
    clients = plugin_context.clients
    # Generate for the current cluster
    for server in cluster_config.servers:
        if not generate_and_distribute(server, clients[server], cluster_config, current_name):
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    stdio.stop_loading("success")
    return plugin_context.return_true()
