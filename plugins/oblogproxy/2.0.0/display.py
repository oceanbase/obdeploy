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