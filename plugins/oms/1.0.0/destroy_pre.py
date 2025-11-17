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


def destroy_pre(plugin_context, *args, **kwargs):

    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf()
    logs_path = global_config.get('logs_mount_path')
    run_path = global_config.get('run_mount_path')
    store_path = global_config.get('store_mount_path')
    if logs_path or run_path or store_path:
        dir_list = ['logs_mount_path', 'run_mount_path', 'store_mount_path']
    else:
        dir_list = ['mount_path']
    sudo_command = {}
    for server in cluster_config.servers:
        sudo_command[server] = 'sudo '
    plugin_context.set_variable('clean_dirs', dir_list)
    plugin_context.set_variable('sudo_command', sudo_command)
    return plugin_context.return_true()