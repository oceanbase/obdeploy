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

from tool import confirm_port, get_port_socket_inode



def stop(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers = {}

    pid_filename = plugin_context.get_variable('pid_filename')
    servers_pid_filenames = plugin_context.get_variable('servers_pid_filenames')
    port_keys = plugin_context.get_variable('port_keys')
    sudo_command = plugin_context.get_variable('sudo_command', default='')

    stdio.start_loading('Stop %s ' % cluster_config.name)
    success = True
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        pid_filename_list = []
        if servers_pid_filenames:
            pid_filename_list = servers_pid_filenames[server]
        if pid_filename:
            pid_filename_list.append(pid_filename)
        for pid_filename in pid_filename_list:
            pid_filenpath = os.path.join(home_path, 'run/%s' % pid_filename)
            pids = client.execute_command('cat %s' % pid_filenpath).stdout.strip().split('\n')
            for pid in pids:
                if pid and client.execute_command(sudo_command + 'ls /proc/%s' % pid):
                    if client.execute_command(sudo_command + 'ls /proc/%s/fd' % pid):
                        stdio.verbose('%s %s[pid: %s] stopping...' % (server, cluster_config.name, pid))
                        client.execute_command(sudo_command + 'kill -9 %s' % pid)
                        port_info = {key: server_config[key] for key in port_keys}
                        servers[server] = {
                            'client': client,
                            'pid': pid,
                            'path': pid_filenpath,
                            **port_info
                        }
                    else:
                        stdio.verbose('failed to stop %s[pid:%s] in %s, permission deny' % (cluster_config.name, pid, server))
                        success = False
                else:
                    stdio.verbose('%s %s is not running' % (server, cluster_config.name))
        if not success:
            stdio.stop_loading('fail')
            return plugin_context.return_true()

    count = 10
    check = lambda client, pid, port: confirm_port(client, pid, port) if count < 5 else get_port_socket_inode(client, port)
    time.sleep(1)
    while count and servers:
        tmp_servers = {}
        for server in servers:
            data = servers[server]
            client = clients[server]
            stdio.verbose('%s check whether the port is released' % server)
            for key in port_keys:
                if data[key] and check(data['client'], data['pid'], data[key]):
                    tmp_servers[server] = data
                    break
                data[key] = ''
            else:
                client.execute_command('rm -rf %s' % data['path'])
                stdio.verbose('%s %s is stopped' % (server, cluster_config.name))
        servers = tmp_servers
        count -= 1
        if count and servers:
            time.sleep(3)
    if servers:
        stdio.stop_loading('fail')
        for server in servers:
            stdio.warn('%s port not released' % server)
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
