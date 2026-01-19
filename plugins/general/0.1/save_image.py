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

import os
from tool import docker_run_sudo_prefix


def save_image(plugin_context, save_dir=None, image_name=None, *args, **kwargs):

    stdio = plugin_context.stdio

    if not save_dir:
        stdio.error("Save directory parameter (save_dir) cannot be empty")
        return plugin_context.return_false(missing_parameter="save_dir")
    
    if not image_name:
        stdio.error("Image name parameter (image_name) cannot be empty")
        return plugin_context.return_false(missing_parameter="image_name")

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients

    image_not_found_servers = []
    
    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_run_sudo_prefix(client)

        ret = client.execute_command('%sdocker images %s --format "{{.Repository}}:{{.Tag}}"' % (prefix, image_name))
        if not ret or not ret.stdout.strip():
            image_not_found_servers.append(str(server))
    
    if image_not_found_servers:
        stdio.error('Image %s not found on the following nodes: %s' % (image_name, ', '.join(image_not_found_servers)))
        return plugin_context.return_false(image_not_found_servers=image_not_found_servers)

    stdio.start_loading('Saving image %s' % image_name)
    save_failed_servers = []
    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_run_sudo_prefix(client)
        mkdir_cmd = '%smkdir -p %s' % (prefix, save_dir)
        if not client.execute_command(mkdir_cmd):
            stdio.error('Failed to create save directory: %s' % save_dir)

        safe_image_name = image_name.replace('/', '_').replace(':', '_')
        save_filename = '%s.tar' % safe_image_name
        save_path = os.path.join(save_dir, save_filename)

        save_cmd = '%sdocker save -o %s %s' % (prefix, save_path, image_name)
        if not client.execute_command(save_cmd):
            save_failed_servers.append(str(server))

    if save_failed_servers:
        stdio.stop_loading('fail')
        stdio.error('Failed to save image %s on the following nodes: %s' % (image_name, ', '.join(save_failed_servers)))
        return plugin_context.return_false(save_failed_servers=save_failed_servers)
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
