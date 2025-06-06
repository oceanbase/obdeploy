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

def passwd_format(passwd):
    return "'{}'".format(passwd.replace("'", "'\"'\"'"))

def display(plugin_context, cursor, config_encrypted, display_encrypt_password='******', *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    if not config_encrypted:
        display_encrypt_password = None
    results = []
    for server in servers:
        api_cursor = cursor.get(server)
        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        url = 'http://{}:{}'.format(ip, api_cursor.port)
        password = cluster_config.get_global_conf_with_default().get('_admin_password_', 'oceanbase') if not display_encrypt_password else display_encrypt_password
        results.append({
            'ip': ip,
            'port': api_cursor.port,
            'user': "admin",
            'password': passwd_format(password),
            'url': url,
            'status': 'active' if api_cursor and api_cursor.status(stdio) else 'inactive'
        })
    stdio.print_list(results, ['url', 'username', 'initial password', 'status'], lambda x: [x['url'], 'admin', x['password'], x['status']], title=cluster_config.name)
    active_result = [r for r in results if r['status'] == 'active']
    info_dict = active_result[0] if len(active_result) > 0 else None
    if info_dict is not None:
        info_dict['type'] = 'web'
    return plugin_context.return_true(info=info_dict)
