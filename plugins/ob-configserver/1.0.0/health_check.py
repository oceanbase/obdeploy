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


from __future__ import absolute_import, division, print_function

import time

from _errno import EC_OBC_PROGRAM_START_ERROR


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients


    stdio.start_loading("ob-configserver program health check")
    time.sleep(1)
    failed = []
    servers = cluster_config.servers
    count = 600
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            if server in tmp_servers:
                continue
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config["home_path"]
            pid_path = '%s/run/ob-configserver.pid' % home_path
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path).stdout.strip()
            if pid:
                if client.execute_command('ls /proc/%s' % pid):
                    stdio.verbose('%s ob-configserver[pid: %s] started', server, pid)
                elif count:
                    tmp_servers.append(server)
                else:
                    failed.append(server)
            else:
                failed.append(server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)

    if failed:
        stdio.stop_loading('fail')
        for server in failed:
            stdio.error(EC_OBC_PROGRAM_START_ERROR.format(server=server))
        plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true()