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

