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

from tool import docker_compose_run_sudo_prefix


class EnvVariables(object):

    def __init__(self, environments, client):
        self.environments = environments
        self.client = client
        self.env_done = {}

    def __enter__(self):
        for env_key, env_value in self.environments.items():
            self.env_done[env_key] = self.client.get_env(env_key)
            self.client.add_env(env_key, env_value, True)

    def __exit__(self, *args, **kwargs):
        for env_key, env_value in self.env_done.items():
            if env_value is not None:
                self.client.add_env(env_key, env_value, True)
            else:
                self.client.del_env(env_key)


def destroy_docker_compose_project(plugin_context, service_names='', *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    env_map = plugin_context.get_variable('env_map')
    services_status = plugin_context.get_variable('services_status')
    stdio.start_loading('Destroy powerrag')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        dc_prefix = docker_compose_run_sudo_prefix(client)
        compose_project = env_map['compose_project'.upper()]
        home_path = server_config.get('home_path')
        cmd_prefix = f"cd {home_path};"
        if services_status[server] or service_names:
            with EnvVariables(env_map, client):
                if not service_names:
                    stop_services = services_status[server]
                else:
                    stop_services = service_names.split(',')

                stop_cmd = cmd_prefix + f"{dc_prefix} docker compose --project-name {compose_project} -f docker-compose.yaml --env-file .env down {' '.join(stop_services)}"
                ret = client.execute_command(stop_cmd)
                if not ret:
                    stdio.stop_loading('fail')
                    stdio.error('%s stop failed: %s' % (server, str(ret.stderr)))
                    return plugin_context.return_false()


    stdio.stop_loading('succeed')
    return plugin_context.return_true()
