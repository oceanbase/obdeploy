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

from tool import NetUtil


def display(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    result = []
    for server in servers:
        api_cursor = cursor.get(server)
        server_config = cluster_config.get_server_conf(server)
        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        result.append({
            'ip': ip,
            'status': 'active' if api_cursor and api_cursor.connect(stdio) else 'inactive',
            'mgragent_http_port': server_config['mgragent_http_port'],
            'monagent_http_port': server_config['monagent_http_port']
        })
        
    stdio.print_list(result, ['ip', 'mgragent_http_port', 'monagent_http_port', 'status'], 
        lambda x: [x['ip'], x['mgragent_http_port'], x['monagent_http_port'], x['status']], title=cluster_config.name)
    plugin_context.return_true()
