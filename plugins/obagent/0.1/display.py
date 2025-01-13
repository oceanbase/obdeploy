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
        client = clients[server]
        config = cluster_config.get_server_conf_with_default(server)
        if config.get('disable_http_basic_auth'):
            auth = ''
        else:
            auth = '--user %s:%s' % (config['http_basic_auth_user'], config['http_basic_auth_password'])
        cmd = '''curl %s -H "Content-Type:application/json" -L "http://%s:%s/metrics/stat"''' % (auth, server.ip, config['server_port'])
        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        result.append({
            'ip': ip,
            'status': 'active' if client.execute_command(cmd) else 'inactive',
            'server_port': config['server_port'],
            'pprof_port': config['pprof_port']
        })
        
    stdio.print_list(result, ['ip', 'server_port', 'pprof_port', 'status'], 
        lambda x: [x['ip'], x['server_port'], x['pprof_port'], x['status']], title=cluster_config.name)
    return plugin_context.return_true()
