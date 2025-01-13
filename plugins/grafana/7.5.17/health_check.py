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


import os
import time
from tool import confirm_port


def health_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_pid = plugin_context.get_variable('servers_pid')

    stdio.start_loading('grafana program health check')
    failed = []
    servers = cluster_config.servers
    count = 600
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            stdio.verbose('%s program health check' % server)
            stdio.verbose('servers_pid: %s ' % servers_pid)
            if servers_pid.get(server):
                for pid in servers_pid[server]:
                    confirm = confirm_port(client, pid, int(server_config["port"]))
                    if confirm:
                        grafana_pid_path = os.path.join(home_path, 'run/grafana.pid')
                        ret = client.execute_command('cat %s' % grafana_pid_path)
                        if ret.stdout.strip('\n') == pid:
                            stdio.verbose('%s grafana[pid: %s] started', server, pid)
                        else:
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s grafana, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start %s grafana' % server)
            else:
                failed.append('failed to start %s grafana' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)

    if failed:
        stdio.stop_loading('failed')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
    return plugin_context.return_true()
