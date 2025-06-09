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

import _errno as err
from tool import get_port_socket_inode


def obshell_port_check(plugin_context, upgrade_check=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    critical = plugin_context.get_variable('critical')
    servers_port = plugin_context.get_variable('servers_port', default={})
    port_check = upgrade_check or plugin_context.get_variable('port_check')
    if not port_check:
        return plugin_context.return_true()

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        ports = servers_port.get(ip, {})
        home_path = server_config['home_path']
        obshell_pid_path = '%s/run/obshell.pid' % home_path
        obshell_pid = client.execute_command('cat %s' % obshell_pid_path).stdout.strip()
        if port_check and not (obshell_pid and client.execute_command('ls /proc/%s' % obshell_pid)):
            stdio.verbose('%s port check' % server)
            port = int(server_config.get('obshell_port'))
            if port in ports:
                critical(
                    server,
                    'port',
                    err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                    [err.SUG_PORT_CONFLICTS.format()]
                )
                continue
            if get_port_socket_inode(client, port):
                critical(server, 'port', err.EC_CONFLICT_PORT.format(server=ip, port=port), [err.SUG_USE_OTHER_PORT.format()])

    return plugin_context.return_true()

