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

import _errno as err

from tool import get_port_socket_inode

def port_check(plugin_context, *args, **kwargs):

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    servers_port = {}
    running_status = plugin_context.get_variable('running_status')
    alert = plugin_context.get_variable('alert')
    critical = plugin_context.get_variable('critical')
    check_pass = plugin_context.get_variable('check_pass')

    for server in cluster_config.servers:
        if running_status and running_status.get(server):
            continue

        client = clients[server]
        ip = server.ip
        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]
        server_config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('%s port check' % server)
        for key in ['listen_port', 'prometheus_listen_port', 'rpc_listen_port']:
            if key == 'rpc_listen_port' and not server_config.get('enable_obproxy_rpc_service'):
                continue
            port = int(server_config[key])
            alert_f = alert if key == 'prometheus_listen_port' else critical
            if port in ports:
                alert_f(server,
                    'port',
                    err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'],
                                                       key=ports[port]['key']),
                    [err.SUG_PORT_CONFLICTS.format()]
                )
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                alert_f(server,
                    'port',
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )
        check_pass(server, 'port')
    get_success = plugin_context.get_variable('get_success')
    if not get_success():
        return plugin_context.return_false()
    return plugin_context.return_true()
