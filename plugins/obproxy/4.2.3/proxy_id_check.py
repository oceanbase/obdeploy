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


def proxy_id_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    running_status = plugin_context.get_variable('running_status')
    critical = plugin_context.get_variable('critical')
    check_pass = plugin_context.get_variable('check_pass')

    for server in cluster_config.servers:
        if running_status and running_status.get(server):
            continue

        server_config = cluster_config.get_server_conf_with_default(server)
        new_cluster_config = kwargs.get('new_cluster_config', None)
        if new_cluster_config:
            server_config = new_cluster_config.get_server_conf_with_default(server)
        client_session_id_version = server_config.get('client_session_id_version')
        proxy_id = server_config.get('proxy_id')
        proxy_id_limits = {
            1: [1, 255],
            2: [1, 8191],
        }
        if proxy_id:
            limit_range = proxy_id_limits.get(client_session_id_version)
            if limit_range:
                min_limit, max_limit = limit_range
                if not (min_limit <= proxy_id <= max_limit):
                    critical(server, 'proxy_id', err.EC_OBPROXY_ID_OVER_LIMIT.format(id=client_session_id_version, limit=str(limit_range)))
        check_pass(server, 'proxy_id')
    plugin_context.return_true()