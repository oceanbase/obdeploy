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

import random


def generate_proxy_id(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    random_num = random.randint(1, 8191 - len(cluster_config.servers))
    num = 0
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client_session_id_version = server_config.get('client_session_id_version', 2)

        if client_session_id_version == 2:
            if server_config.get('proxy_id', None) is None:
                cluster_config.update_server_conf(server, 'proxy_id', random_num + num, False)
                cluster_config.update_server_conf(server, 'client_session_id_version', client_session_id_version, False)
            num += 1
    return plugin_context.return_true()