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

from tool import docker_run_sudo_prefix


def destroy_container(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_config = cluster_config.get_global_conf()
    container_name = global_config.get('container_name')
    if not container_name:
        return plugin_context.return_false()

    stdio.start_loading('destroy %s container' % cluster_config.name)

    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_run_sudo_prefix(client)
        if not client.execute_command('%sdocker rm -f %s' % (prefix, container_name)):
            stdio.stop_loading('fail')
            stdio.verbose('%s: % destroy fail' % (server, container_name))
            return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()