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


def display(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    clients = plugin_context.clients
    results = []
    for server in servers:
        server_config = cluster_config.get_server_conf(server)
        port = int(server_config["service_port"])
        ip = server.ip
        client = clients[server]

        remote_pid_path = '%s/run/oblogproxy-%s-%s.pid' % (server_config['home_path'], server.ip, server_config["service_port"])
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            results.append({
                'ip': ip,
                'port': port,
                'url':  'obclient -h%s -P%s' % (server.ip, server_config['service_port']),
                'status': 'active'
            })
    stdio.print_list(results, ['ip', 'port', 'status'], lambda x: [x['ip'], x['port'], x['status']], title=cluster_config.name)
    stdio.print(results[0]['url'] if results else '')
    stdio.print('')
    return plugin_context.return_true()