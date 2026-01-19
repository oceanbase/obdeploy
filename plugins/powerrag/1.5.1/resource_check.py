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

import os

from _types import Capacity

import _errno as err
from tool import get_port_socket_inode


def resource_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_port = {}
    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')
    get_success = plugin_context.get_variable('get_success')
    if plugin_context.get_variable('resource_check_pass'):
        for server in cluster_config.servers:
            check_pass(server, 'port')
            check_pass(server, 'cpu')
            check_pass(server, 'memory')
        return plugin_context.return_true()

    for server in cluster_config.servers:

        server_config = cluster_config.get_server_conf_with_default(server)
        ip = server.ip
        client = clients[server]

        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]
        stdio.verbose('%s port check' % server)
        port_keys = ['expose_powerrag_api_port']
        port_check_pass = True
        for key in port_keys:
            port = int(server_config[key])
            if port in ports:
                critical(server,
                    'port',
                    err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                    [err.SUG_PORT_CONFLICTS.format()]
                )
                port_check_pass = False
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                port_check_pass = False
                critical(server,
                    'port',
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )
        if port_check_pass:
            check_pass(server, 'port')

        default_cpu_count = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l").stdout.strip()
        if not default_cpu_count or (int(default_cpu_count) < 4):
           critical(server,
               'cpu',
               err.EC_CPU_CORE_NOT_ENOUGH.format(server=server, current=default_cpu_count, required=4)
           )
        else:
            check_pass(server, 'cpu')

        memory = client.execute_command("grep MemTotal /proc/meminfo | sed 's/^[^0-9]*//g'|sed 's/kB//g'").stdout.strip()
        if not memory or (int(memory) // 1024 // 1024 < 16):
            critical(server,
                'memory',
                err.EC_OBSERVER_NOT_ENOUGH_MEMORY.format(server=server, free=Capacity(int(memory)), need='16G')
            )
        else:
            check_pass(server, 'memory')

        compose_project = server_config['compose_project']
        bootstrap_path = os.path.join(server_config['home_path'], '.bootstrap')
        cmd = 'ls %s' % bootstrap_path
        compose_project_check = True
        if not client.execute_command(cmd):
            ret = client.execute_command('docker compose --project-name %s ps --format "{{json .}}"' % compose_project)
            if ret:
                lines = ret.stdout.strip().splitlines()
                if len(lines) > 0:
                    compose_project_check = False
                    critical(server,
                             'project_name',
                             err.EC_POWERRAG_PROJECT_NAME_USED.format(ip=server, project_name=compose_project)
                             )
        if compose_project_check:
            check_pass(server, 'project_name')

    if not get_success():
        return plugin_context.return_false()

    return plugin_context.return_true()
