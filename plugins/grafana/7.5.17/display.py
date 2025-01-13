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


stdio = None


def display(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    results = []
    if plugin_context.get_variable('is_restart'):
        cursor = plugin_context.get_return('connect').get_return('cursor')

    for server in servers:
        server_config = cluster_config.get_server_conf(server)
        api_cursor = cursor.get(server)

        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        user = api_cursor.user
        protocol = api_cursor.protocol
        if 'prometheus' in cluster_config.depends:
            url = '%s://%s:%s/d/oceanbase' % (protocol, ip, server_config['port'])
        else:
            url = '%s://%s:%s' % (protocol, ip, server_config['port'])
        results.append({
            'ip': ip,
            'port': server_config['port'],
            'user': user,
            'password': api_cursor.password,
            'url': url,
            'status': 'active' if api_cursor and api_cursor.connect(stdio) else 'inactive'
        })

    stdio.print_list(results, [ 'url', 'user', 'password', 'status'], lambda x: [x['url'], x['user'], x['password'], x['status']], title=cluster_config.name)
    active_result = [r for r in results if r['status'] == 'active']
    info_dict = active_result[0] if len(active_result) > 0 else None
    if info_dict is not None:
        info_dict['type'] = 'web'
    return plugin_context.return_true(info=info_dict)
