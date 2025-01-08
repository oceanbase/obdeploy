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
from copy import deepcopy


def display(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    results = []
    start_env = plugin_context.get_variable('start_env')
    cursor = plugin_context.get_return('connect', spacename='ocp-server-ce').get_return('cursor')
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
            'password': server_config['admin_password'] if not original_global_conf.get('admin_password', '') else original_global_conf['admin_password'],
            'url': url,
            'status': 'active' if api_cursor and api_cursor.status(stdio) else 'inactive'
        })
    stdio.print_list(results, ['url', 'username', 'password', 'status'], lambda x: [x['url'], 'admin', server_config['admin_password'] if not original_global_conf.get('admin_password', '') else original_global_conf['admin_password'], x['status']], title='%s' % cluster_config.name)
    active_result = [r for r in results if r['status'] == 'active']
    info_dict = active_result[0] if len(active_result) > 0 else None
    if info_dict is not None:
        info_dict['type'] = 'web'
    return plugin_context.return_true(info=info_dict)
