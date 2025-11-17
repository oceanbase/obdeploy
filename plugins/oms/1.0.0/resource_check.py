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

from _types import Capacity

import _errno as err
from tool import get_port_socket_inode


def resource_check(plugin_context, work_dir_check=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_port = {}
    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')
    if plugin_context.get_variable('resource_check_pass'):
        for server in cluster_config.servers:
            check_pass(server, 'port')
        return plugin_context.return_true()

    for server in cluster_config.servers:

        server_config = cluster_config.get_server_conf_with_default(server)
        ip = server.ip
        client = clients[server]

        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]
        stdio.verbose('%s port check' % server)
        port_keys = ['ghana_server_port', 'nginx_server_port', 'cm_server_port', 'supervisor_server_port', 'sshd_server_port']
        for key in port_keys:
            port = int(server_config[key])
            if port in ports:
                critical(server,
                    'port',
                    err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                    [err.SUG_PORT_CONFLICTS.format()]
                )
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                critical(server,
                    'port',
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )
        check_pass(server, 'port')

        default_cpu_count = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l").stdout.strip()
        if not default_cpu_count or (int(default_cpu_count) < 9):
            stdio.warn('Insufficient resources: CPU cores fewer than 8, which will affect the speed of data migration.')

        memory = client.execute_command("grep MemTotal /proc/meminfo | sed 's/^[^0-9]*//g'|sed 's/kB//g'").stdout.strip()
        if not memory or (int(memory) // 1024 // 1024 < 16):
            stdio.warn('Insufficient resources: Memory less than 16 GB. Each migration task requires at least 12 GB of memory for both full and incremental migration. Insufficient memory can cause the migration task to fail.')

        logs_path = server_config.get('logs_mount_path')
        run_path = server_config.get('run_mount_path')
        store_path = server_config.get('store_mount_path')
        if logs_path or run_path or store_path:
            need_init_paths = [logs_path, run_path, store_path]
        else:
            need_init_paths = [server_config['mount_path']]
        for path in need_init_paths:
            if Capacity(client.execute_command(f"df -BG {path} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes < 50 << 30:
               stdio.warn('Insufficient resources(%s): Available disk space less than 50 GB. Migration task logs and incremental data will occupy disk space. If there is not enough space, the migration task may fail.' % path)


    return plugin_context.return_true()
