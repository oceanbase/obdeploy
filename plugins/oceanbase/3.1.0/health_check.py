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

from _errno import EC_OBSERVER_FAIL_TO_START


def health_check(plugin_context, *args, **kwargs):
    if plugin_context.get_variable('scale_out'):
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('observer program health check')
    time.sleep(3)
    failed = []
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/observer.pid' % home_path
        stdio.verbose('%s program health check' % server)
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            stdio.verbose('%s observer[pid: %s] started', server, remote_pid)
        else:
            failed.append(EC_OBSERVER_FAIL_TO_START.format(server=server))
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')

    restart_manager = plugin_context.get_variable('restart_manager')
    if restart_manager:
        restart_manager.close()

    return plugin_context.return_true()
