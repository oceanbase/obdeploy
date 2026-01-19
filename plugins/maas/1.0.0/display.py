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
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    global_config = cluster_config.get_global_conf()
    servers_info = []
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        port = server_config.get('port', 8001)
        prometheus_host_port = server_config.get('prometheus_host_port', 9090)
        info = {
            'server': server.ip,
            'maas_service_url': f"http://{server.ip}:{port}",
            'prometheus_url': f"http://{server.ip}:{prometheus_host_port}"
        }
        servers_info.append(info)

    stdio.print_list(servers_info, ['server', 'maas_service_url', 'prometheus_url'],
                     lambda x: [x['server'], x['maas_service_url'], x['prometheus_url']],
                     title=cluster_config.name)
    if servers_info:
        url = servers_info[0].get('maas_service_url')
        return plugin_context.return_true(url=url)
    return plugin_context.return_true()

