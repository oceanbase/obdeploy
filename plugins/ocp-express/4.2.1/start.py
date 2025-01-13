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

import json
import os

from _types import Capacity, CapacityWithB
from tool import FileUtil, YamlLoader, ConfigUtil


def start(plugin_context, start_env=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    get_key = plugin_context.get_variable('get_key')
    get_plain_public_key = plugin_context.get_variable('get_plain_public_key')
    rsa_private_sign = plugin_context.get_variable('rsa_private_sign')
    jdbc_url = plugin_context.get_variable('jdbc_url')

    if not start_env:
        return plugin_context.return_false()

    exclude_keys = ["home_path", "port", "jdbc_url", "jdbc_username", "jdbc_password", "cluster_name", "ob_cluster_id",
                    "root_sys_password", "server_addresses", "agent_username", "agent_password", "memory_size"]

    repository_dir = None
    for repository in plugin_context.repositories:
        if repository.name == cluster_config.name:
            repository_dir = repository.repository_dir
            break
    with FileUtil.open(os.path.join(repository_dir, 'conf/ocp-express-config-mapper.yaml')) as f:
        data = YamlLoader(stdio=stdio).load(f)
    config_mapper = data.get('config_mapper', {})
    server_pid = {}
    success = True
    stdio.start_loading("Start ocp-express")
    for server in cluster_config.servers:
        client = clients[server]
        server_config = start_env[server]
        home_path = server_config['home_path']
        jdbc_username = server_config['jdbc_username']
        jdbc_password = server_config['jdbc_password']
        port = server_config['port']
        pid_path = os.path.join(home_path, 'run/ocp-express.pid')
        pids = client.execute_command("cat %s" % pid_path).stdout.strip()
        bootstrap_flag = client.execute_command('ls %s' % os.path.join(home_path, '.bootstrapped'))
        if pids and all([client.execute_command('ls /proc/%s' % pid) for pid in pids.split('\n')]):
            server_pid[server] = pids
            continue
        if getattr(options, 'without_parameter', False) and bootstrap_flag:
            use_parameter = False
        else:
            use_parameter = True

        if server_config.get('encrypt_password', False):
            private_key, public_key = get_key(client, os.path.join(home_path, 'conf'), stdio)
            public_key_str = get_plain_public_key(public_key)
            jdbc_password = rsa_private_sign(jdbc_password, private_key)
        else:
            public_key_str = ""
        memory_size = server_config['memory_size']
        jvm_memory_option = "-Xms{0} -Xmx{0}".format(str(Capacity(Capacity(memory_size).bytes * 0.5, 0)).lower())
        java_bin = server_config['java_bin']
        client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
        cmd = '{java_bin} -jar {jvm_memory_option} -DJDBC_URL={jdbc_url} -DJDBC_USERNAME={jdbc_username}' \
              ' -DPUBLIC_KEY={public_key} {home_path}/lib/ocp-express-server.jar --port={port}'.format(
                java_bin=java_bin,
                home_path=home_path,
                port=port,
                jdbc_url=jdbc_url,
                jdbc_username=jdbc_username,
                public_key=public_key_str,
                jvm_memory_option=jvm_memory_option
        )
        if "log_dir" not in server_config:
            log_dir = os.path.join(home_path, 'log')
        else:
            log_dir = server_config["log_dir"]
        server_config["logging_file_name"] = os.path.join(log_dir, 'ocp-express.log')
        if use_parameter:
            cmd += ' --bootstrap --progress-log={}'.format(os.path.join(log_dir, 'bootstrap.log'))
            for key in server_config:
                if key not in exclude_keys and key in config_mapper:
                    if key == 'logging_file_total_size_cap':
                        cmd += ' --with-property=ocp.logging.file.total.size.cap:{}'.format(CapacityWithB(server_config[key]))
                        continue
                    cmd += ' --with-property={}:{}'.format(config_mapper[key], server_config[key])
        elif not bootstrap_flag:
            cmd += ' --bootstrap --progress-log={}'.format(os.path.join(log_dir, 'bootstrap.log'))
        data = {
            "cluster": {
                "name": server_config["cluster_name"],
                "obClusterId": server_config["ob_cluster_id"],
                "rootSysPassword": server_config["root_sys_password"],
                "serverAddresses": server_config["server_addresses"],
            },
            "agentUsername": server_config["agent_username"],
            "agentPassword": server_config["agent_password"],
            "agentAuthType": "OCP_DIGEST"
        }

        admin_passwd = cluster_config.get_global_conf_with_default().get("admin_passwd", '')

        client.add_env('OCP_EXPRESS_INIT_PROPERTIES',  json.dumps(data) if client._is_local else ConfigUtil.passwd_format(json.dumps(data)), rewrite=True)
        client.add_env('OCP_EXPRESS_ADMIN_PASSWD', admin_passwd if client._is_local else ConfigUtil.passwd_format(admin_passwd), rewrite=True)
        client.add_env('JDBC_PASSWORD', jdbc_password if client._is_local else ConfigUtil.passwd_format(jdbc_password), rewrite=True)

        client.execute_command("cd {}; bash -c '{} > /dev/null 2>&1 &'".format(home_path, cmd))
        ret = client.execute_command("ps -aux | grep '%s' | grep -v grep | awk '{print $2}' " % cmd)
        if ret:
            server_pid[server] = ret.stdout.strip()
            if not server_pid[server]:
                stdio.error("failed to start {} ocp express".format(server))
                success = False
                continue
            client.write_file(server_pid[server], os.path.join(home_path, 'run/ocp-express.pid'))
    plugin_context.set_variable('server_pid', server_pid)
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
