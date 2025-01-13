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
import re
import time

from tool import confirm_port


def health_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    cmd_args_map = plugin_context.get_variable('cmd_args_map')

    prometheusd = plugin_context.get_variable("prometheusd")
    stdio.start_loading('prometheus program health check')
    failed = []
    pid_path = {}
    servers = cluster_config.servers
    count = 600

    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config['home_path']
            pid_path[server] = os.path.join(home_path, 'run/prometheus.pid')
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config["home_path"]
            stdio.verbose('%s program health check' % server)
            remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if remote_pid:
                for pid in re.findall('\d+', remote_pid):
                    confirm = confirm_port(client, pid, int(server_config["port"]))
                    if confirm:
                        prometheusd_pid_path = os.path.join(home_path, 'run/prometheusd.pid')
                        if client.execute_command("pid=`cat %s` && ls /proc/$pid" % prometheusd_pid_path):
                            stdio.verbose('%s prometheusd[pid: %s] started', server, pid)
                        else:
                            prometheusd(home_path, client, server, cmd_args_map[server], stdio=stdio)
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s prometheus, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start {} prometheus'.format(server))
            elif not count:
                failed.append('failed to start {} prometheus'.format(server))
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
        plugin_context.return_true(need_bootstrap=True)

