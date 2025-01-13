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
    return plugin_context.return_true()
