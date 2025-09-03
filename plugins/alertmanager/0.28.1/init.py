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

import os.path

from _errno import EC_FAIL_TO_INIT_PATH, EC_CLEAN_PATH_FAILED, InitDirFailedErrorMessage, EC_CONFIG_CONFLICT_DIR, EC_COMPONENT_DIR_NOT_EMPTY

def _clean(server, client, path, stdio=None):
    ret = client.execute_command('rm -fr %s' % path, timeout=-1)
    if not ret:
        stdio.warn(EC_CLEAN_PATH_FAILED.format(server=server, path=path))
        return False
    else:
        stdio.verbose('%s:%s cleaned' % (server, path))
        return True

def init(plugin_context, source_option=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes alertmanager work home')
    servers_dirs = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        ip = server.ip
        if ip not in servers_dirs:
            servers_dirs[ip] = {}
        dirs = servers_dirs[ip]
        home_path = server_config['home_path']
        data_dir = server_config.get('data_dir')
        log_dir = server_config.get('log_dir')
        if not data_dir:
            server_config['data_dir'] = os.path.join(home_path, 'data')
        if not log_dir:
            server_config['log_dir'] = os.path.join(home_path, 'log')
        keys = ['home_path', 'data_dir', 'log_dir']
        for key in keys:
            path = server_config[key]
            if path in dirs:
                global_ret = False
                stdio.error(EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']))
                continue
            dirs[path] = {
                'server': server,
                'key': key,
            }
        need_clean = force
        if clean and not force:
            if client.execute_command(
                    'bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(
                        home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                global_ret = False
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True
        if need_clean:
            port = server_config['port']
            address = server_config['address']
            client.execute_command(
                "pkill -9 -u `whoami` -f '^{home_path}/alertmanager --config.file={home_path}/alertmanager.yaml --web.listen-address={address}:{port}'".format(
                    home_path=home_path, address=address, port=port))
            if not _clean(server, client, home_path, stdio=stdio):
                global_ret = False
                continue
            if data_dir and not _clean(server, client, data_dir, stdio=stdio):
                global_ret = False
                continue
            if log_dir and not _clean(server, client, log_dir, stdio=stdio):
                global_ret = False
                continue
        path_map = {
            'data_dir': 'data',
            'log_dir': 'log'
        }
        for key, value in path_map.items():
            link_path = os.path.join(home_path, value)
            target_path = server_config.get(key, link_path)
            if client.execute_command('mkdir -p %s' % target_path):
                ret = client.execute_command('ls %s' % target_path)
                if not ret or ret.stdout.strip():
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=target_path)))
                    source_option == "deploy" and stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                    global_ret = False
                    continue
                client.execute_command("if [ ! '%s' -ef '%s' ]; then ln -sf %s %s; fi" % (target_path, link_path, target_path, link_path))
            else:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=target_path)))
                continue

    
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')