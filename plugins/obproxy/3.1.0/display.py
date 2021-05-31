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


def display(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    result = []
    for server in servers:
        data = {
            'ip': server.ip,
            'status': 'inactive',
            'listen_port': '-',
            'prometheus_listen_port': '-'
        }
        try:
            cursor[server].execute('show proxyconfig like "%port"')
            for item in cursor[server].fetchall():
                if item['name'] in data:
                    data[item['name']] = item['value']
            data['status'] = 'active'
        except:
            stdio.exception('')
            pass
        result.append(data)
    stdio.print_list(result, ['ip', 'port', 'prometheus_port', 'status'], 
        lambda x: [x['ip'], x['listen_port'], x['prometheus_listen_port'], x['status']], title='obproxy')
    plugin_context.return_true()
