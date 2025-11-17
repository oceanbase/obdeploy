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

import json
import time
import requests

from tool import docker_run_sudo_prefix


def health_check(plugin_context, new_cluster_config=None, **kwargs):
    cluster_config = plugin_context.cluster_config
    if new_cluster_config:
        cluster_config = new_cluster_config
    stdio = plugin_context.stdio
    stdio.start_loading('OMS health check')
    clients = plugin_context.clients

    regions_server_map = plugin_context.get_variable('regions_server_map')
    check_pass_server = []
    init_pass_server = []
    times = 900
    global_config = cluster_config.get_global_conf()
    container_name = global_config.get('container_name')
    finally_script_is_docker_init = plugin_context.get_variable('finally_script_is_docker_init', default=True)

    t = None
    while times > 0:
        times -= 1 if not t else t
        t = 0
        for region, servers in regions_server_map.items():
            for server in servers:
                client = clients[server]
                if finally_script_is_docker_init:
                    if server not in init_pass_server:
                        prefix = docker_run_sudo_prefix(client)
                        ret = client.execute_command("%sdocker logs %s|tail -1" % (prefix, container_name), stdio=stdio)
                        if not ret or ret.stdout.strip() != 'OMS service start successfully':
                            continue
                        init_pass_server.append(server)
                if server in check_pass_server:
                    continue
                server_config = cluster_config.get_server_conf(server)
                url = f"http://{server.ip}:{str(server_config.get('nginx_server_port', 8089))}/oms/health"
                stdio.verbose(f'check health url: {url}')
                ret = None
                try:
                    ret = requests.get(url, timeout=4)
                    if json.loads(ret.content).get('data').get('healthy') is True:
                        check_pass_server.append(server)
                except Exception as e:
                    if not isinstance(e, requests.exceptions.ConnectionError):
                        if ret is not None:
                            stdio.verbose(f'response: {ret.content}')
                        else:
                            t = 5
                        stdio.verbose(f'check health error: {e}')
                    continue
        if len(check_pass_server) == len(cluster_config.servers):
            break
        time.sleep(1)

    if len(check_pass_server) == len(cluster_config.servers):
        stdio.stop_loading('succeed')
    else:
        stdio.stop_loading('fail')
        check_fail_servers = list(set(cluster_config.servers).difference(set(check_pass_server)))
        servers_str = ','.join([server.ip for server in check_fail_servers])
        stdio.error('%s: health check failed' % servers_str)
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()