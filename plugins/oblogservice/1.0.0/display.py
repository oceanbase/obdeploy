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

from oblogservice_util import get_cluster_id, get_local_ip, http_addr, rpc_addr


def display(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    global_conf = cluster_config.get_global_conf()
    cluster_id = global_conf.get('cluster_id')
    results = []

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        client = clients[server]
        local_ip = get_local_ip(server, server_config)
        cid = get_cluster_id(cluster_config, server_config)
        home_path = server_config['home_path']
        ret = client.execute_command(
            "ps -aux | grep '%s/bin/oblogservice -g' | grep -v grep | awk '{print $2}'" % home_path
        )
        active = bool(ret and ret.stdout.strip())
        results.append({
            'server': str(server),
            'cluster_id': cid,
            'rpc': rpc_addr(server, server_config),
            'http': http_addr(server, server_config),
            'home_path': home_path,
            'status': 'active' if active else 'inactive',
        })

    stdio.print_list(
        results,
        ['server', 'cluster_id', 'rpc', 'http', 'status'],
        lambda x: [x['server'], x['cluster_id'], x['rpc'], x['http'], x['status']],
        title=cluster_config.name,
    )
    if cluster_id is not None:
        stdio.print('logservice_cluster_id=%s (use in ObServer LOGSERVICE_ACCESS_POINT)' % cluster_id)
    stdio.print('')
    return plugin_context.return_true()
