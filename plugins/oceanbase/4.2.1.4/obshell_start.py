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

from _errno import EC_OBSERVER_FAIL_TO_START_OCS
from tool import ConfigUtil


def obshell_start(plugin_context, *args, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    start_obshell = plugin_context.get_variable('start_obshell', default=True)
    scale_out = plugin_context.get_variable('scale_out')
    if not start_obshell and not need_bootstrap and not scale_out:
        return plugin_context.return_true()
    stdio = plugin_context.stdio
    stdio.verbose('start_obshell: %s' % start_obshell)
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio.start_loading('obshell start')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
        if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
            stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
        else:
            # start obshell
            server_config = cluster_config.get_server_conf(server)
            password = server_config.get('root_password', '')
            client.add_env('OB_ROOT_PASSWORD', password if client._is_local else ConfigUtil.passwd_format(password))
            cmd = 'cd %s; %s/bin/obshell admin start --ip %s --port %s' % (server_config['home_path'], server_config['home_path'], server.ip, server_config['obshell_port'])
            stdio.verbose('start obshell: %s' % cmd)
            if not client.execute_command(cmd):
                stdio.error('%s obshell failed', server)
                stdio.stop_loading('fail')
                return
    stdio.stop_loading('succeed')

    # check obshell health
    failed = []
    stdio.start_loading('obshell program health check')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
        stdio.verbose('Get %s obshell[pid: %s]', server, obshell_pid)
        if obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid):
            stdio.verbose('%s obshell[pid: %s] started', server, obshell_pid)
        else:
            failed.append(EC_OBSERVER_FAIL_TO_START_OCS.format(server=server))
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')

    return plugin_context.return_true()
