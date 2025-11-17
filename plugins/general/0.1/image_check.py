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

from tool import docker_run_sudo_prefix


def image_check(plugin_context, image_name=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    image_name = image_name or (cluster_config.image_name + ':' + cluster_config.tag)
    failed_servers = []
    image_hash = None
    for server in cluster_config.servers:
        client = clients[server]
        prefix = docker_run_sudo_prefix(client)
        ret = client.execute_command('%sdocker images %s --digests --format "{{json .}}"' % (prefix, image_name)).stdout.strip()
        if not ret or not json.loads(ret):
            failed_servers.append(str(server))
        else:
            if not image_hash:
                image_hash = json.loads(ret).get('ID')
            else:
                if image_hash != json.loads(ret).get('ID'):
                    stdio.error('%s: The hash values of the mirrored data are inconsistent(%s).' % (server, json.loads(ret).get('ID')))
                    return plugin_context.return_false()

    if failed_servers:
        stdio.error('%s: %s is not found' % (','.join(failed_servers), image_name))
        return plugin_context.return_false()
    return plugin_context.return_true(image_hash=image_hash)