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

from tool import docker_run_sudo_prefix


def docker_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    failed_servers = []
    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_run_sudo_prefix(client)
        if not client.execute_command('%sdocker --version' % prefix):
            failed_servers.append(server.ip)
    if failed_servers:
        stdio.error('%s: docker is not installed' % ','.join(failed_servers))
        return plugin_context.return_false()
    return plugin_context.return_true()