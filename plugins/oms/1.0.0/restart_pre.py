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

from tool import set_plugin_context_variables


def restart_pre(plugin_context, *args, **kwargs):
    new_clients = kwargs.get('new_clients')
    new_deploy_config = kwargs.get('new_deploy_config')
    cluster_config = plugin_context.cluster_config

    global_config = cluster_config.get_global_conf()
    logs_path = global_config.get('logs_mount_path')
    run_path = global_config.get('run_mount_path')
    store_path = global_config.get('store_mount_path')
    if logs_path or run_path or store_path:
        dir_list = ['logs_mount_path', 'run_mount_path', 'store_mount_path']
    else:
        dir_list = ['mount_path']
    variables_dict = {
        "clients": plugin_context.clients,
        "dir_list": dir_list,
        "new_clients": new_clients,
        "new_deploy_config": new_deploy_config
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()



