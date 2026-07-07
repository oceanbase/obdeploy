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

from oblogservice_util import OBLOGSERVICE_MIN_SERVERS, find_running_pid, get_bootstrap_server, get_local_ip


def _running_servers(plugin_context):
    running_servers = plugin_context.get_variable('running_servers', default=set())
    return running_servers or set()


def start_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    critical = plugin_context.get_variable('critical')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    port_check = plugin_context.get_variable('port_check', default=True)
    servers_port = plugin_context.get_variable('servers_port', default={})
    get_success = plugin_context.get_variable('get_success')
    running_servers = _running_servers(plugin_context)

    stdio.start_loading('Check before start oblogservice')
    server_count = len(cluster_config.servers)
    if server_count < OBLOGSERVICE_MIN_SERVERS:
        anchor = cluster_config.servers[0]
        critical(
            anchor,
            'servers',
            'oblogservice requires at least %d nodes, got %d'
            % (OBLOGSERVICE_MIN_SERVERS, server_count),
            [],
        )

    bootstrap_server_name = cluster_config.get_global_conf().get('bootstrap_server')
    if bootstrap_server_name and get_bootstrap_server(cluster_config) is None:
        anchor = cluster_config.servers[0]
        critical(
            anchor,
            'bootstrap_server',
            err.EC_OBLOGSERVICE_INVALID_BOOTSTRAP_SERVER.format(
                bootstrap_server=bootstrap_server_name),
            [],
        )

    if port_check:
        for server in cluster_config.servers:
            if server in running_servers:
                continue
            server_config = cluster_config.get_server_conf_with_default(server)
            client = clients[server]
            home_path = server_config['home_path']
            ip = server.ip
            local_ip = get_local_ip(server, server_config)
            port = int(server_config['port'])
            http_port = int(server_config['http_port'])
            ports = servers_port.setdefault(ip, {})

            if port == http_port:
                critical(
                    server,
                    'port',
                    err.EC_CONFIG_CONFLICT_PORT.format(
                        server1=server, port=port, server2=server, key='http_port'),
                    [err.SUG_PORT_CONFLICTS.format()],
                )

            for key, p in (('port', port), ('http_port', http_port)):
                if p in ports:
                    critical(
                        server,
                        key,
                        err.EC_CONFIG_CONFLICT_PORT.format(
                            server1=server,
                            port=p,
                            server2=ports[p]['server'],
                            key=ports[p]['key'],
                        ),
                        [err.SUG_PORT_CONFLICTS.format()],
                    )
                else:
                    ports[p] = {'server': server, 'key': key}
                if get_port_socket_inode(client, p):
                    if find_running_pid(client, home_path, p):
                        continue
                    critical(
                        server,
                        key,
                        err.EC_CONFLICT_PORT.format(server=local_ip, port=p),
                        [err.SUG_USE_OTHER_PORT.format()],
                    )

    for server in cluster_config.servers:
        if server in running_servers:
            continue
        wait_2_pass(server)

    if get_success and get_success():
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
    return plugin_context.return_false()
