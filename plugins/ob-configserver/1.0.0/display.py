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

