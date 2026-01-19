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

from tool import docker_compose_run_sudo_prefix


def get_services_status(plugin_context, *args, **kwargs):
    """
    Get the status of each service in docker compose project.
    Returns detailed status information for each service.
    """
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_config = cluster_config.get_global_conf_with_default()
    project_name = global_config.get('compose_project')
    
    if not project_name:
        stdio.error('project_name is not set in global config')
        return plugin_context.return_false()
    
    services_status = {}
    
    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_compose_run_sudo_prefix(client)
        
        # Get all services status in JSON format
        cmd = '%sdocker compose --project-name %s ps -a --format "{{json .}}"' % (prefix, project_name)
        ret = client.execute_command(cmd)
        
        server_services = {}
        
        if ret and ret.stdout.strip():
            # Parse each line as JSON (each line represents one service)
            for line in ret.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    service_info = json.loads(line)
                    service_name = service_info.get('Service', '')
                    if not service_name:
                        continue
                    
                    server_services[service_name] = {
                        'state': service_info.get('State', ''),
                        'status': service_info.get('Status', ''),
                        'health': service_info.get('Health', ''),
                        'service': service_info.get('Service', ''),
                        'image': service_info.get('Image', ''),
                        'ports': service_info.get('Publishers', ''),

                    }
                except (json.JSONDecodeError, ValueError) as e:
                    stdio.warn('Failed to parse service status JSON: %s, error: %s' % (line, str(e)))
                    continue
        
        services_status[server] = server_services

    plugin_context.set_variable('services_status', services_status)
    
    return plugin_context.return_true()

