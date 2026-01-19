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

from _stdio import FormatText
from tool import get_option


def display(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    server_config = cluster_config.get_server_conf(cluster_config.servers[0])
    services_status = plugin_context.get_variable('services_status')
    display_data = []
    for server, services in services_status.items():
        for name, info in services.items():
            display_data.append({
                "name": name,
                "status": info['status'],
                "state": info['state']
            })
        stdio.print_list(display_data, ['name', 'status', 'state'], lambda x: [x['name'], x['status'], x['state']], title=f"{server.ip} Services Status")
    stdio.print(FormatText.success("PowerRAG WEB URL: http://{0}:{1}".format(cluster_config.servers[0].ip, server_config.get('expose_powerrag_api_port'))))

    return plugin_context.return_true()

