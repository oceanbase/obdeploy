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


stdio = None


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "cat  /proc/net/{tcp,udp} | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def start_check(plugin_context, alert_lv='error', *args, **kwargs):
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    success = True
    alert = getattr(stdio, alert_lv)
    servers_port = {}
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]
        server_config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('%s port check' % server)
        for key in ['listen_port', 'prometheus_listen_port']:
            port = int(server_config[key])
            if port in ports:
                alert('%s: %s port is used for %s\'s %s' % (server, port, ports[port]['server'], ports[port]['key']))
                success = False
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                alert('%s:%s port is already used' % (ip, port))
                success = False
    if success:
        plugin_context.return_true()