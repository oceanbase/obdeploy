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

import os
import time

from _errno import EC_CONFLICT_PORT
from tool import confirm_port


def prometheusd(home_path, client, server, args, start_only=False, stdio=None):
    prometheusd_path = os.path.join(os.path.split(__file__)[0], 'prometheusd.sh')
    remote_path = os.path.join(home_path, 'prometheusd.sh')
    shell = 'cd {} && bash prometheusd.sh {}'.format(home_path, ' '.join(args))
    if start_only:
        shell += ' --start-only'
    if not client.put_file(prometheusd_path, remote_path, stdio=stdio):
        stdio.error('failed to send prometheusd.sh to {}'.format(server))
        return False
    ret = client.execute_command(shell)
    if not ret:
        stdio.error('failed to start {} prometheus.'.format(server))
        return False
    return True


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    pid_path = {}
    cmd_args_map = plugin_context.get_variable('cmd_args_map')

    stdio.start_loading('Start promethues')
    for server in cluster_config.servers:
        cmd_items = cmd_args_map[server]
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        port = server_config['port']
        pid_path[server] = os.path.join(home_path, 'run/prometheus.pid')
        remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/{}'.format(remote_pid)):
                if confirm_port(client, remote_pid, int(server_config["port"])):
                    continue
                stdio.stop_loading('fail')
                stdio.error(EC_CONFLICT_PORT.format(server=server.ip, port=port))
                return plugin_context.return_false()
        if not prometheusd(home_path, client, server, cmd_items, start_only=True, stdio=stdio) or not client.execute_command('pid=`cat %s` && ls /proc/$pid' % pid_path[server]):
            stdio.stop_loading('fail')
            return False

    plugin_context.set_variable("prometheusd", prometheusd)
    time.sleep(1)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
