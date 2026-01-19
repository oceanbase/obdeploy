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
from tool import docker_compose_run_sudo_prefix


def status(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    cluster_status = {}
    global_config = cluster_config.get_global_conf_with_default()
    project_name = global_config.get('compose_project')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config.get('home_path')
        cmd_prefix = f"cd {home_path};"
        client = clients[server]
        dc_prefix = docker_compose_run_sudo_prefix(client)
        cluster_status[server] = ClusterStatus.STATUS_STOPPED.value
        ret = client.execute_command(cmd_prefix +'%sdocker compose --project-name %s ps --format "{{json .}}"' % (dc_prefix, project_name))
        if ret and ret.stdout.strip():
            cluster_status[server] = ClusterStatus.STATUS_RUNNING.value
    return plugin_context.return_true(cluster_status=cluster_status)