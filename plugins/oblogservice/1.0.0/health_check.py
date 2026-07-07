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

from oblogservice_util import find_running_pid, get_local_ip, pid_path


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    need_bootstrap = plugin_context.get_variable('need_bootstrap', default=True)
    running_servers = plugin_context.get_variable('running_servers', default=set()) or set()
    servers = [
        server for server in cluster_config.servers
        if server not in running_servers
    ]
    if not servers:
        return plugin_context.return_true(need_bootstrap=need_bootstrap)

    stdio.start_loading('oblogservice health check')
    count = 60
    failed = []
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf_with_default(server)
            client = clients[server]
            local_ip = get_local_ip(server, server_config)
            port = int(server_config['port'])
            home_path = server_config['home_path']
            remote_pid_path = pid_path(home_path, local_ip, port)
            running_pid = find_running_pid(client, home_path, port)
            if running_pid:
                client.execute_command('echo "%s" > %s' % (running_pid, remote_pid_path))
                stdio.verbose('%s oblogservice[pid:%s] started', server, running_pid)
            else:
                if count:
                    tmp_servers.append(server)
                else:
                    failed.append('failed to start oblogservice on %s' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)

    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true(need_bootstrap=need_bootstrap)
