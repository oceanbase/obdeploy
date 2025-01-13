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


def reload_pre(plugin_context, new_cluster_config, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    stdio = plugin_context.stdio

    proxy_id_limits = {
        1: [1, 255],
        2: [1, 8191],
    }

    for server in servers:
        server_config = new_cluster_config.get_server_conf(server)
        client_session_id_version = server_config.get('client_session_id_version')
        proxy_id = server_config.get('proxy_id')
        if proxy_id and client_session_id_version == 1:
            limit_range = proxy_id_limits.get(client_session_id_version)
            if limit_range:
                min_limit, max_limit = limit_range
                if not (min_limit <= proxy_id <= max_limit):
                    stdio.error(err.EC_OBPROXY_ID_OVER_LIMIT.format(id=client_session_id_version, limit=str(limit_range)))
                    return plugin_context.return_false()
                
    return plugin_context.return_true()