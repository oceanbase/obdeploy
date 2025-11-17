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
from tool import docker_run_sudo_prefix


def reload(plugin_context, new_cluster_config=None, upgrade=False, *args, **kwargs):
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    stdio.start_loading('Reload oms')
    if new_cluster_config or upgrade:
        global_config = cluster_config.get_global_conf()
        container_name = global_config.get('container_name')
        regions_server_map = plugin_context.get_variable('regions_server_map')
        for region, servers in regions_server_map.items():
            for server in servers:
                client = clients[server]
                prefix = docker_run_sudo_prefix(client)
                ret = client.execute_command("%sdocker exec %s /bin/bash -c './docker_init.sh' " % (prefix, container_name))
                if not ret:
                    stdio.stop_loading('fail')
                    stdio.error('%s docker exec %s /bin/bash -c \'./docker_init.sh\' failed' % (server, container_name))
                    return plugin_context.return_false()

    plugin_context.set_variable('finally_script_is_docker_init', False)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()