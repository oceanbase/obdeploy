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
