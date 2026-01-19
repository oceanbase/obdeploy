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

from tool import docker_compose_run_sudo_prefix, get_option


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


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    service_names = get_option(plugin_context.options, 'service_names', '')
    env_map = plugin_context.get_variable('env_map')
    services_status = plugin_context.get_variable('services_status')
    stdio.start_loading('Start powerrag')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        dc_prefix = docker_compose_run_sudo_prefix(client)
        compose_project = env_map['compose_project'.upper()]
        home_path = server_config.get('home_path')
        cmd_prefix = f"cd {home_path};"
        wait_time = env_map.get('wait_timeout') or 900
        with EnvVariables(env_map, client):
            if not service_names:
                not_running_services = []
                if services_status[server]:
                    for server_name, info in services_status[server].items():
                        if info['state'] == 'running':
                            stdio.warn('%s: %s is running.' % (server, server_name))
                            not_running_services.append(server_name)
                first_start_services = plugin_context.get_variable('first_start_services')
                second_start_services = plugin_context.get_variable('second_start_services')
                third_start_services = plugin_context.get_variable('third_start_services')
                for start_services in [first_start_services, second_start_services, third_start_services]:
                    real_start_services = list(set(start_services) - set(not_running_services))
                    if not real_start_services:
                        continue
                    start_cmd1 = cmd_prefix + f"{dc_prefix} docker compose --project-name {compose_project} -f docker-compose.yaml --env-file .env up -d --wait --wait-timeout {wait_time} {' '.join(real_start_services)}"
                    ret = client.execute_command(str(start_cmd1))
                    if not ret:
                        stdio.stop_loading('fail')
                        stdio.error('%s start failed: %s. Error: %s' % (server, ','.join(first_start_services), ret.stderr))
                        return plugin_context.return_false()
            else:
                for server_name in service_names.split(','):
                    if services_status[server]:
                        if server_name in services_status[server] and services_status[server][server_name]['status'] == 'running':
                            stdio.warn('%s: %s is running.' % (server, server_name))
                            continue
                    start_cmd = cmd_prefix + f"{dc_prefix} docker compose --project-name {compose_project} -f docker-compose.yaml --env-file .env up -d --wait --wait-timeout {wait_time} {server_name}"
                    ret = client.execute_command(start_cmd)
                    if not ret:
                        stdio.stop_loading('fail')
                        stdio.error('%s start failed: %s. Error: %s' % (server, ','.join(first_start_services), ret.stderr))
                        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
