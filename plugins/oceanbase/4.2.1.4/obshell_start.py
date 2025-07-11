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

import time

from _errno import EC_OBSERVER_FAIL_TO_START_OCS
from tool import ConfigUtil


def obshell_start(plugin_context, *args, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    start_obshell = plugin_context.get_variable('start_obshell', default=True)
    scale_out = plugin_context.get_variable('scale_out')
    if not start_obshell and not need_bootstrap and not scale_out:
        return plugin_context.return_true()
    stdio = plugin_context.stdio
    stdio.verbose('start_obshell: %s' % start_obshell)
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio.start_loading('obshell start')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
        if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
            stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
        else:
            # start obshell
            server_config = cluster_config.get_server_conf(server)
            password = server_config.get('root_password', '')
            client.add_env('OB_ROOT_PASSWORD', password if client._is_local else ConfigUtil.passwd_format(password), True)
            cmd = 'cd %s; %s/bin/obshell admin start --ip %s --port %s' % (server_config['home_path'], server_config['home_path'], server.ip, server_config['obshell_port'])
            stdio.verbose('start obshell: %s' % cmd)
            res = client.execute_command(cmd)
            if not res:
                if res.stderr:
                    if '[ERROR]' in res.stderr:
                        stdio.print(res.stderr)
                    else:
                        stdio.error(res.stderr)
                stdio.stop_loading('fail')
                return
    stdio.stop_loading('succeed')

    # check obshell health
    failed = []
    stdio.start_loading('obshell program health check')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
        stdio.verbose('Get %s obshell[pid: %s]', server, obshell_pid)
        if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
            stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
        else:
            failed.append(EC_OBSERVER_FAIL_TO_START_OCS.format(server=server))
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')

    return plugin_context.return_true()
