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


def passwd_format(passwd):
    return "'{}'".format(passwd.replace("'", "'\"'\"'"))


def display(plugin_context, cursor, display_encrypt_password='******', *args, **kwargs):
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
            cmd = 'obclient -h%s -P%s -u%s %s-Doceanbase -A \n' % (server.ip, server_config['listen_port'], user, '-p%s ' % ((passwd_format(password) if password else '') if not display_encrypt_password else passwd_format(display_encrypt_password)))
            break

    if (with_observer and server_config.get('obproxy_sys_password', '')) or not with_observer:
        user = 'root@proxysys'
        password = server_config.get('obproxy_sys_password', '')
        info_dict['user'] = user
        info_dict['password'] = password
        cmd = 'obclient -h%s -P%s -u%s %s-Doceanbase -A \n' % (server.ip, server_config['listen_port'], user, '-p%s ' % ((passwd_format(password) if password else '') if not display_encrypt_password else passwd_format(display_encrypt_password)))

    stdio.print(cmd)
    info_dict['cmd'] = cmd
    return plugin_context.return_true(info=info_dict)
