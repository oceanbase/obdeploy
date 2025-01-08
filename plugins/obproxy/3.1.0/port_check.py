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
        for key in ['listen_port', 'prometheus_listen_port']:
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
