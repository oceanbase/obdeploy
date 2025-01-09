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


def obshell_stop(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('Stop obshell')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s obshell stopping ...' % (server))
        home_path = server_config['home_path']
        cmd = 'cd %s; %s/bin/obshell admin stop' % (home_path, home_path)
        if not client.execute_command(cmd):
            stdio.stop_loading('fail')
            return
        # check obshell is stopped
        remote_pid_path = '%s/run/obshell.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ps uax | egrep " %s " | grep -v grep' % remote_pid):
            stdio.stop_loading('fail')
            return
        remote_pid_path = '%s/run/daemon.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ps uax | egrep " %s " | grep -v grep' % remote_pid):
            stdio.stop_loading('fail')
            return

    stdio.stop_loading('succeed')

    plugin_context.return_true()