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

from tool import confirm_port


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    server_pid = plugin_context.get_variable('server_pid', default={})

    stdio.start_loading("%s program health check" % cluster_config.name)
    failed = []
    servers = cluster_config.servers
    count = 600
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            stdio.verbose('%s program health check' % server)
            pids_stat = {}
            for pid in server_pid[server].split("\n"):
                pids_stat[pid] = None
                if not client.execute_command('ls /proc/{}'.format(pid)):
                    pids_stat[pid] = False
                    continue
                confirm = confirm_port(client, pid, int(server_config["service_port"]))
                if confirm:
                    pids_stat[pid] = True
                    break
            if any(pids_stat.values()):
                for pid in pids_stat:
                    if pids_stat[pid]:
                        stdio.verbose('%s %s[pid: %s] started', server, cluster_config.name, pid)
                continue
            if all([stat is False for stat in pids_stat.values()]):
                failed.append('failed to start %s %s' % (server, cluster_config.name))
            elif count:
                tmp_servers.append(server)
                stdio.verbose('failed to start %s %s, remaining retries: %d' % (server, cluster_config.name, count))
            else:
                failed.append('failed to start %s %s' % (server, cluster_config.name))
        servers = tmp_servers
        if servers and count:
            time.sleep(3)
    if failed:
        stdio.stop_loading('failed')
        for msg in failed:
            stdio.error(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()