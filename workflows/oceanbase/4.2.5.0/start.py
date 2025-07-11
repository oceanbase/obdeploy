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

import const
import os


def start(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    server_config = cluster_config.get_server_conf(cluster_config.servers[0])
    client = None
    component_kwargs = kwargs.get("component_kwargs")
    if component_kwargs:
        clients = component_kwargs.get("new_clients")
        client = list(clients.values())[0]
    if not client:
        return plugin_context.return_false()
    component_name = cluster_config.name
    workflow.add(const.STAGE_FIRST, 'configserver_pre', 'start_pre', 'start', 'health_check', 'connect', 'bootstrap', 'user_pre', 'create_user', 'alter_sys_unit')
    if component_name in [const.COMP_OB_STANDALONE, const.COMP_OB_CE]:
        workflow.add(const.STAGE_FIRST, 'obshell_start', 'obshell_bootstrap')
    install_utils = cluster_config.get_global_conf().get('install_utils', False)
    utils_flag = os.path.join(server_config['home_path'], 'bin', 'ob_admin')
    cmd = 'ls %s' % utils_flag
    if install_utils and not client.execute_command(cmd):
        workflow.add(const.STAGE_SECOND, 'install_ob_utils')
    enable_observer_auto = cluster_config.get_global_conf().get('enable_auto_start', False)
    auto_start_flag = os.path.join(server_config['home_path'], '.enable_auto_start')
    cmd = 'ls %s' % auto_start_flag
    if enable_observer_auto and not client.execute_command(cmd):
        workflow.add(const.STAGE_SECOND, 'enable_auto_start')
    plugin_context.return_true()

