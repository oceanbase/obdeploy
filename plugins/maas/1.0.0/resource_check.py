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
    get_success = plugin_context.get_variable('get_success')
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
        port_keys = ['prometheus_host_port', 'port']
        check_port = True
        for key in port_keys:
            port = int(server_config[key])
            if port in ports:
                check_port = False
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
                check_port = False
                critical(server,
                    'port',
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )
        if check_port:
            check_pass(server, 'port')

        data_dir = server_config.get('data_dir')
        if Capacity(client.execute_command(f"df -BG {data_dir} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes < 50 << 30:
            critical(server, 'path', err.EC_MAAS_NOT_ENOUGH_DISK.format(server=ip, disk=data_dir, need='50G'))
        else:
            check_pass(server, 'path')

    if not get_success():
        return plugin_context.return_false()


    return plugin_context.return_true()
