# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


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
