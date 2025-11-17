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

from ssh import SshClient, SshConfig
from tool import docker_run_sudo_prefix


def get_clients(host, username, password, port, stdio):
    client = SshClient(
        SshConfig(
            host,
            username,
            password,
            None,
            port
        ),
        stdio=stdio
    )
    if not client.connect():
        return None
    return client


def get_docker_images(plugin_context, ssh_info, image_name, *args, **kwargs):
    stdio = plugin_context.stdio
    servers = ssh_info['servers']
    username = ssh_info['username']
    password = ssh_info['password']
    port = ssh_info['port']

    servers_client_map = {}
    for host in servers.split(','):
        client = get_clients(host, username, password, port, stdio)
        if client is None:
            msg = 'Please provide a user with root or sudo privileges so that obd can install and deploy the product.'
            stdio.error(msg)
            return plugin_context.return_false(connect_error=msg)
        servers_client_map[host] = client

    images_num_map = {}
    image_hash_map = {}
    not_found_servers = []
    docker_not_installed_servers = []
    search_images_error = ''
    host_image_info_map = {}
    for host, client in servers_client_map.items():
        host_image_ids = []
        prefix = docker_run_sudo_prefix(client)
        if not client.execute_command('%sdocker --version' % prefix):
            docker_not_installed_servers.append(host)
            continue
        rv = client.execute_command('%sdocker images --format "{{json .}}"| grep %s' % (prefix, image_name))
        if not rv:
            not_found_servers.append(host)
            continue
        host_image_info_map[host] = ''
        versions_str = host_image_info_map[host]
        ret = rv.stdout.strip()
        for image_info in ret.split('\n'):
            image_info = json.loads(image_info)
            if not versions_str:
                versions_str = image_info['Tag']
            else:
                versions_str += ',' + image_info['Tag']
            image_hash_map[image_info['ID']] = image_info['Repository'] + ':' + image_info['Tag']
            if image_info['ID'] not in host_image_ids:
                host_image_ids.append(image_info['ID'])
                if image_info['ID'] not in images_num_map:
                    images_num_map[image_info['ID']] = 1
                else:
                    images_num_map[image_info['ID']] += 1

    images = []
    if not_found_servers:
        search_images_error = 'OMS image not found. Ensure that the same version of the image file is uploaded to all nodes.'
    elif docker_not_installed_servers:
        search_images_error = 'Docker is not installed on the following nodes: %s' % ','.join(docker_not_installed_servers)
    elif images_num_map:
        for image_id, num in images_num_map.items():
            if num == len(servers.split(',')):
                images.append({"name": image_hash_map[image_id].split(':')[0], "id": image_id, "version": image_hash_map[image_id].split(':')[1]})
        if not images:
            error_info = ''
            for host, image_tags in host_image_info_map.items():
                error_info += '%s: %s\n' % (host, image_tags)
            search_images_error = 'OMS image versions are inconsistent. Ensure that the same image version exists on all nodes. Image version details: %s' % error_info

    if search_images_error:
        return plugin_context.return_false(images=images, search_images_error=search_images_error)

    return plugin_context.return_true(images=images)