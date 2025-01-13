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

import re
import time

from tool import confirm_port


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    servers = cluster_config.servers

    stdio.start_loading('start oblogproxy health_check')
    count = 600
    failed = []
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            stdio.verbose('%s program health check' % server)
            remote_pid_path = "%s/run/oblogproxy-%s-%s.pid" % (server_config['home_path'], server.ip, server_config['service_port'])
            remote_pid = client.execute_command("cat %s" % remote_pid_path).stdout.strip()
            if remote_pid:
                for pid in re.findall('\d+', remote_pid):
                    confirm = confirm_port(client, pid, int(server_config["service_port"]))
                    if confirm:
                        if client.execute_command("ls /proc/%s" % remote_pid):
                            stdio.verbose('%s oblogproxy[pid: %s] started', server, pid)
                        else:
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s oblogproxy, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start %s oblogproxy' % server)
            else:
                failed.append('failed to start %s oblogproxy' % server)

        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
            plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=False)