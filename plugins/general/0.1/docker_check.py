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

from tool import docker_compose_run_sudo_prefix, docker_run_sudo_prefix
from _rpm import Version


def docker_check(plugin_context, docker_compose_check=False, docker_version=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    docker_not_installed_servers = []
    docker_compose_not_installed_servers = []
    for server in cluster_config.servers:
        client = clients[server]
        dc_prefix = docker_compose_run_sudo_prefix(client)
        d_prefix = docker_run_sudo_prefix(client)
        ret = client.execute_command('%sdocker --version' % d_prefix)
        if not ret:
            docker_not_installed_servers.append(server.ip)
        if ret and ret.stdout and docker_version:
            if Version(docker_version) > Version(ret.stdout.strip()):
                stdio.error('%s: Docker version must be greater than %s' % (server.ip, docker_version))
                return plugin_context.return_false()
               
        if docker_compose_check and not client.execute_command('%sdocker compose --version' % dc_prefix):
            docker_compose_not_installed_servers.append(server.ip)
    if docker_not_installed_servers:
        stdio.error('%s: docker is not installed' % ','.join(docker_not_installed_servers))
    if docker_compose_not_installed_servers:
        stdio.error('%s: docker-compose is not installed' % ','.join(docker_compose_not_installed_servers))

    if docker_not_installed_servers or docker_compose_not_installed_servers:
        return plugin_context.return_false()
    return plugin_context.return_true()