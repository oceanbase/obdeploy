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

from oblogservice_util import get_local_ip, pid_path, validate_oblogservice_oceanbase_combo


def _stop_oblogservice(client, home_path, local_ip, port, stdio, server):
    remote_pid_path = pid_path(home_path, local_ip, port)
    remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
    if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
        stdio.verbose('%s oblogservice[pid:%s] stopping ...' % (server, remote_pid))
        client.execute_command('kill -9 %s' % remote_pid)
    ret = client.execute_command(
        "ps -aux | grep '%s/bin/oblogservice -g' | grep -v grep | awk '{print $2}'" % home_path
    )
    if ret and ret.stdout.strip():
        for pid in ret.stdout.strip().split('\n'):
            client.execute_command('kill -9 %s' % pid)


def init(plugin_context, source_option=None, *args, **kwargs):
    stdio = plugin_context.stdio
    if not validate_oblogservice_oceanbase_combo(
        plugin_context.components,
        plugin_context.repositories,
        stdio,
    ):
        return plugin_context.return_false()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    mkdir_keys = plugin_context.get_variable('mkdir_keys')
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes oblogservice work home')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        local_ip = get_local_ip(server, server_config)
        port = int(server_config['port'])
        stdio.verbose('%s init oblogservice work home', server)
        need_clean = force
        if clean and not force:
            if client.execute_command(
                'bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)
            ):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                global_ret = False
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True

        if need_clean:
            _stop_oblogservice(client, home_path, local_ip, port, stdio, server)
            ret = client.execute_command('rm -fr %s' % home_path, timeout=-1)
            if not ret:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
                continue
        else:
            if client.execute_command('mkdir -p %s' % home_path):
                ret = client.execute_command('ls %s' % home_path)
                if not ret or ret.stdout.strip():
                    global_ret = False
                    stdio.error(
                        EC_FAIL_TO_INIT_PATH.format(
                            server=server,
                            key='home path',
                            msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path),
                        )
                    )
                    source_option == 'deploy' and stdio.error(
                        EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True
                    )
                    continue
            else:
                global_ret = False
                stdio.error(
                    EC_FAIL_TO_INIT_PATH.format(
                        server=server,
                        key='home path',
                        msg=InitDirFailedErrorMessage.CREATE_FAILED.format(path=home_path),
                    )
                )
                continue

        if not client.execute_command(mkdir_keys % home_path):
            global_ret = False
            stdio.error(
                EC_FAIL_TO_INIT_PATH.format(
                    server=server,
                    key='home path',
                    msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path),
                )
            )

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
    return plugin_context.return_false()
