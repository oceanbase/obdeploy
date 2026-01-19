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

from _deploy import ClusterStatus
from tool import docker_run_sudo_prefix


def status(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    cluster_status = {}
    global_config = cluster_config.get_global_conf()
    container_name = global_config.get('container_name')
    for server in cluster_config.servers:
        client = clients[server]
        cluster_status[server] = ClusterStatus.STATUS_STOPPED.value
        prefix = docker_run_sudo_prefix(client)
        ret = client.execute_command('%sdocker ps --filter "name=%s " --format "{{json .}}"' % (prefix, container_name)).stdout.strip()
        if ret and json.loads(ret).get('State') == 'running':
            cluster_status[server] = ClusterStatus.STATUS_RUNNING.value
    return plugin_context.return_true(cluster_status=cluster_status)