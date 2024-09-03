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
import json

import requests
from tool import NetUtil


def display(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config

    result = []
    for server in cluster_config.servers:
        api_cursor = cursor.get(server)
        server_config = cluster_config.get_server_conf(server)
        ip = api_cursor.ip
        client = clients[server]
        if client.is_localhost():
            ip = NetUtil.get_host_ip()
        port = api_cursor.port
        vip_address = server_config.get('vip_address', ip)
        vip_port = server_config.get('vip_port', port)
        home_path = server_config["home_path"]
        pid_path = '%s/run/ob-configserver.pid' % home_path
        pid = client.execute_command('cat %s' % pid_path).stdout.strip()
        result.append({
            'server': ip,
            'port': port,
            'vip_address': vip_address,
            'vip_port': vip_port,
            'status': 'active' if api_cursor.status else 'inactive',
            'pid': pid
        })

    stdio.print_list(result, ['server', 'port', 'vip_address', 'vip_port', 'status', 'pid'],
                 lambda x: [x['server'], x['port'], x['vip_address'], x['vip_port'], x['status'], x['pid']],
                 title=cluster_config.name)
    if result:
        cmd = "curl -s 'http://{0}:{1}/services?Action=GetObProxyConfig'".format(result[0]['server'], result[0]['port'])
        stdio.print(cmd)
    plugin_context.return_true()

