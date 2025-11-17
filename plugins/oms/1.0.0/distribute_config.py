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
import time

from ssh import get_root_permission_client
from tool import YamlLoader, get_sudo_prefix, docker_run_sudo_prefix


class DoubleQuotedString(str):
    pass


def double_quoted_representer(representer, data):
    return representer.represent_scalar('tag:yaml.org,2002:str', data, style='"')


def distribute_config(plugin_context, new_cluster_config=None, *args, **kwargs):

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_config = cluster_config.get_global_conf()

    regions_server_map = plugin_context.get_variable('regions_server_map')
    regions_config = plugin_context.get_variable('regions_config')

    stdio.verbose('distribute config')
    yaml = YamlLoader(stdio)
    yaml.representer.add_representer(DoubleQuotedString, double_quoted_representer)
    for region, config in regions_config.items():
        for server in regions_server_map[region]:
            client = clients[server]
            container_name = global_config.get('container_name')
            prefix = docker_run_sudo_prefix(client)
            ret = client.execute_command('%sdocker ps -a --filter "name=%s" --format "{{json .}}"' % (prefix, container_name)).stdout.strip()
            if not ret or new_cluster_config:
                server_config = cluster_config.get_server_conf(server)
                run_path = server_config.get('run_mount_path') or (server_config.get('mount_path') + '/run')
                generate_config_dir = os.path.join(os.path.dirname(run_path), 'config')
                if not client.execute_command('ls {0}'.format(generate_config_dir)):
                    mkdir_cmd = 'mkdir -p {0}'.format(generate_config_dir)
                    client.execute_command(mkdir_cmd)

                quoted_data = {}
                for k, v in config.items():
                    quoted_key = DoubleQuotedString(k)
                    if isinstance(v, str):
                        quoted_value = DoubleQuotedString(v)
                    elif isinstance(v, list):
                        for _v in v:
                            if isinstance(_v, str):
                                _v = DoubleQuotedString(_v)
                        quoted_value = v
                    else:
                        quoted_value = v
                    quoted_data[quoted_key] = quoted_value

                if client.execute_command('ls {0}'.format(os.path.join(run_path, 'config.yaml*'))):
                    sudo_client = get_root_permission_client(client, server, stdio)
                    if not sudo_client:
                        stdio.stop_loading('fail')
                        return plugin_context.return_false()
                    prefix = get_sudo_prefix(sudo_client)
                    if client.execute_command('ls {0}'.format(os.path.join(run_path, 'config.yaml'))):
                        command = f"echo '{yaml.dumps(quoted_data)}' | {prefix} tee {os.path.join(run_path, 'config.yaml')} > /dev/null"
                        if not client.execute_command(command):
                            stdio.stop_loading('fail')
                            stdio.error('upgrade OMS config failed')
                            return plugin_context.return_false()
                else:
                    if not client.write_file(yaml.dumps(quoted_data), os.path.join(run_path, 'config.yaml')):
                        stdio.stop_loading('fail')
                        return plugin_context.return_false()

    return plugin_context.return_true()