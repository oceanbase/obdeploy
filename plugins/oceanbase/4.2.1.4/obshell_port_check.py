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


def obshell_port_check(plugin_context, upgrade_check=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    critical = plugin_context.get_variable('critical')
    servers_port = plugin_context.get_variable('servers_port')
    port_check = upgrade_check or plugin_context.get_variable('port_check')
    if not port_check:
        return plugin_context.return_true()

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        ports = servers_port[ip]
        if port_check:
            stdio.verbose('%s port check' % server)
            port = int(server_config.get('obshell_port'))
            if port in ports:
                critical(
                    server,
                    'port',
                    err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                    [err.SUG_PORT_CONFLICTS.format()]
                )
                continue
            if get_port_socket_inode(client, port):
                critical(server, 'port', err.EC_CONFLICT_PORT.format(server=ip, port=port), [err.SUG_USE_OTHER_PORT.format()])

    return plugin_context.return_true()

