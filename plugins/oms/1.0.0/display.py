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
from urllib.parse import urlparse

from tool import add_http_prefix


def display(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    global_config = cluster_config.get_global_conf()
    regions = global_config.get('regions', [])
    regions_info = []
    if len(cluster_config.servers) == 1:
        server_config = cluster_config.get_server_conf(cluster_config.servers[0])
        regions_info = [{'region': 'default', 'cm_url': f"http://{cluster_config.servers[0].ip}:{server_config.get('nginx_server_port', '8089')}", 'default': 'true', 'nodes': cluster_config.servers[0].ip}]
    else:
        class Region(object):
            def __init__(self, data):
                self.region_data = {}
                self.load_data(data)

            def __getitem__(self, item):
                return self.region_data[item]

            def get(self, key, default=None):
                return self.region_data.get(key, default)

            def load_data(self, data):
                if isinstance(data, dict):
                    self.region_data = data
                else:
                    raise TypeError('region data must be dict.')
        regions_server_map = {}
        for region in regions:
            region = Region(region)
            info = {}
            regions_server_map[region] = []
            info['region'] = region.get('cm_region', 'default')
            info['cm_url'] = region['cm_nodes'][0] + ":" + str(global_config.get('nginx_server_port', '8089'))
            info['default'] = region['cm_is_default']
            info['nodes'] = ','.join(region['cm_nodes'])
            regions_info.append(info)

    stdio.print_list(regions_info, ['region', 'url', 'cm_is_default', 'nodes'],
                     lambda x: [x['region'], x['cm_url'], x['default'], x['nodes']],
                     title=cluster_config.name)
    url = regions_info[0].get('cm_url')
    return plugin_context.return_true(url=url)

