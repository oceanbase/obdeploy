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

from tool import YamlLoader, NetUtil

yaml = YamlLoader()


def display(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    results = []
    for server in servers:
        api_cursor = cursor.get(server)
        server_config = cluster_config.get_server_conf(server)
        protocol = 'https' if api_cursor.ssl else 'http'
        user = api_cursor.username
        password = api_cursor.password
        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        url = '%s://%s:%s' % (protocol, ip, server_config['port'])
        results.append({
            'ip': ip,
            'port': api_cursor.port,
            'url': url,
            'user': user if user else '',
            'password': password if password else '',
            'status': 'active' if api_cursor and api_cursor.connect(stdio) else 'inactive'
        })
    stdio.print_list(results, ['url', 'user', 'password', 'status'], lambda x: [x['url'], x['user'], x['password'], x['status']], title=cluster_config.name)
    active_result = [r for r in results if r['status'] == 'active']
    info_dict = active_result[0] if len(active_result) > 0 else None
    if info_dict is not None:
        info_dict['type'] = 'web'
    return plugin_context.return_true(info=info_dict)
