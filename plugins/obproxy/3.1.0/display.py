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


def passwd_format(passwd):
    return "'{}'".format(passwd.replace("'", "'\"'\"'"))


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
        res = cursor[server].fetchall('show proxyconfig like "%port"', exc_level='verbose')
        if res:
            for item in res:
                if item['name'] in data:
                    data[item['name']] = item['value']
            data['status'] = 'active'
        else:
            continue
        result.append(data)
    stdio.print_list(result, ['ip', 'port', 'prometheus_port', 'status'],
        lambda x: [x['ip'], x['listen_port'], x['prometheus_listen_port'], x['status']], title=cluster_config.name)
    server = servers[0]
    with_observer = False
    server_config = cluster_config.get_server_conf(server)
    cmd = ''
    info_dict = {
        "type": "db",
        "ip": server.ip,
        "port": server_config['listen_port']
    }
    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            ob_config = cluster_config.get_depend_config(comp)
            if not ob_config:
                continue
            user = 'root'
            password = ob_config.get('root_password', '')
            with_observer = True
            info_dict['user'] = user
            info_dict['password'] = password
            cmd = 'obclient -h%s -P%s -u%s %s-Doceanbase -A \n' % (server.ip, server_config['listen_port'], user, '-p%s ' % passwd_format(password) if password else '')
            break

    if (with_observer and server_config.get('obproxy_sys_password', '')) or not with_observer:
        user = 'root@proxysys'
        password = server_config.get('obproxy_sys_password', '')
        info_dict['user'] = user
        info_dict['password'] = password
        cmd = 'obclient -h%s -P%s -u%s %s-Doceanbase -A \n' % (server.ip, server_config['listen_port'], user, '-p%s ' % passwd_format(password) if password else '')

    stdio.print(cmd)
    info_dict['cmd'] = cmd
    plugin_context.return_true(info=info_dict)
