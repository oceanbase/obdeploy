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

from _errno import EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY


def init(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes obproxy work home')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        stdio.verbose('%s init cluster work home', server)
        need_clean = force
        if clean and not force:
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                if owner != client.config.username:
                    global_ret = False
                    err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                    continue
            need_clean = True

        if need_clean:
            client.execute_command("pkill -9 -u `whoami` -f '^bash {home_path}/obproxyd.sh {home_path} {ip} {port} daemon$'".format(home_path=home_path, ip=server.ip, port=server_config.get('listen_port')))
            client.execute_command("pkill -9 -u `whoami` -f '^%s/bin/obproxy --listen_port %s'" % (home_path, server_config.get('listen_port')))
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                global_ret = False
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            ret = client.execute_command('rm -fr %s' % home_path, timeout=-1)
            if not ret:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
                continue

        if not (clean or force):
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
                stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)
                continue

        if not client.execute_command("bash -c 'mkdir -p %s/{run,bin,lib}'" % home_path):
            global_ret = False
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path)))
            
    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()