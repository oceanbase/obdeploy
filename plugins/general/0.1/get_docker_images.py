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


def get_client(host, username, password, port, stdio):
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
    connect_result = client.connect(exit=False, stdio_func='error')
    if connect_result is not True:
        return None, getattr(connect_result, 'msg', '')
    return client, ''


def get_docker_prefix(client):
    if client.execute_command('docker images'):
        return ''
    if client.execute_command('[ "$(id -u)" = "0" ]'):
        return ''
    if client.execute_command('sudo -n docker images'):
        return 'sudo -n '
    return None


def get_docker_images(plugin_context, ssh_info, image_name, *args, **kwargs):
    stdio = plugin_context.stdio
    servers = ssh_info['servers']
    username = ssh_info['username']
    password = ssh_info['password']
    port = ssh_info['port']

    hosts = [host.strip() for host in servers.split(',') if host.strip()]
    servers_client_map = {}
    for host in hosts:
        client, connect_error = get_client(host, username, password, port, stdio)
        if client is None:
            msg = connect_error or '%s@%s:%s SSH connection failed.' % (username, host, port)
            stdio.error(msg)
            return plugin_context.return_false(connect_error=msg)
        servers_client_map[host] = client

    not_found_servers = []
    docker_not_installed_servers = []
    search_images_error = ''
    host_image_info_map = {}
    images_num_map = {}
    image_hash_map = {}
    permission_denied_servers = []
    for host, client in servers_client_map.items():
        host_image_keys = set()
        if not client.execute_command('command -v docker >/dev/null 2>&1'):
            docker_not_installed_servers.append(host)
            continue
        prefix = get_docker_prefix(client)
        if prefix is None:
            permission_denied_servers.append(host)
            continue
        rv = client.execute_command('%sdocker images --no-trunc --format "{{json .}}"| grep %s' % (prefix, image_name))
        if not rv:
            not_found_servers.append(host)
            continue
        host_images = []
        ret = rv.stdout.strip()
        for image_info in ret.split('\n'):
            image_info = json.loads(image_info)
            host_images.append('%s:%s' % (image_info['Repository'], image_info['Tag']))
            image_id = image_info['ID'].split(':')[-1]
            image_key = (image_id, image_info['Repository'], image_info['Tag'])
            image_hash_map[image_key] = {
                'name': image_info['Repository'],
                'id': 'sha256:%s' % image_id,
                'version': image_info['Tag']
            }
            if image_key not in host_image_keys:
                host_image_keys.add(image_key)
                images_num_map[image_key] = images_num_map.get(image_key, 0) + 1
        host_image_info_map[host] = ','.join(host_images)

    images = []
    if permission_denied_servers:
        search_images_error = (
            'The deployment user cannot access Docker on the following nodes: %s. '
            'Grant the user Docker access or password-free sudo privileges.' %
            ','.join(permission_denied_servers)
        )
    elif not_found_servers:
        search_images_error = 'OMS image not found. Ensure that the same version of the image file is uploaded to all nodes.'
    elif docker_not_installed_servers:
        search_images_error = 'Docker is not installed on the following nodes: %s' % ','.join(docker_not_installed_servers)
    elif images_num_map:
        images = [
            image_hash_map[image_key] for image_key, count in images_num_map.items()
            if count == len(servers_client_map)
        ]
        if not images:
            error_info = ''
            for host, image_tags in host_image_info_map.items():
                error_info += '%s: %s\n' % (host, image_tags)
            search_images_error = 'OMS image versions are inconsistent. Ensure that the same image version exists on all nodes. Image version details: %s' % error_info

    if search_images_error:
        return plugin_context.return_false(images=images, search_images_error=search_images_error)

    return plugin_context.return_true(images=images)
