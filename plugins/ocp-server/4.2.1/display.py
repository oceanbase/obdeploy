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

from const import ENCRYPT_PASSWORD
from tool import NetUtil
from copy import deepcopy


def display(plugin_context, config_encrypted, display_encrypt_password='******', *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    if not config_encrypted:
        display_encrypt_password = None
    results = []
    start_env = plugin_context.get_variable('start_env')
    cursor = plugin_context.get_return('connect', spacename=cluster_config.name).get_return('cursor')
    for server in servers:
        api_cursor = cursor.get(server)
        server_config = start_env[server]
        original_global_conf = cluster_config.get_original_global_conf()
        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        url = 'http://{}:{}'.format(ip, api_cursor.port)
        results.append({
            'ip': ip,
            'port': api_cursor.port,
            'user': "admin",
            'password': (server_config['admin_password'] if not original_global_conf.get('admin_password', '') else original_global_conf['admin_password']),
            'url': url,
            'status': 'active' if api_cursor and api_cursor.status(stdio) else 'inactive'
        })
    stdio.print_list(results, ['url', 'username', 'password', 'status'], lambda x: [x['url'], 'admin', (server_config['admin_password'] if not original_global_conf.get('admin_password', '') else original_global_conf['admin_password']) if not display_encrypt_password else display_encrypt_password, x['status']], title='%s' % cluster_config.name)
    active_result = [r for r in results if r['status'] == 'active']
    info_dict = active_result[0] if len(active_result) > 0 else None
    if info_dict is not None:
        info_dict['type'] = 'web'
    return plugin_context.return_true(info=info_dict)
