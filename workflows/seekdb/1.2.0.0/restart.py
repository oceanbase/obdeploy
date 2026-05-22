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


def restart(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.get_variable('clients')
    new_clients = plugin_context.get_variable('new_clients')
    new_deploy_config = plugin_context.get_variable('new_deploy_config')
    new_cluster_config = new_deploy_config.components[kwargs['repository'].name] if new_deploy_config else {}

    workflow.add(const.STAGE_FIRST, 'seekdb_standby_detect', 'obshell_stop', 'stop')
    if new_clients:
        workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {"new_clients": new_clients}, 'chown_dir')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config},
                             'configserver_pre', 'start_pre', 'start', 'health_check')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config}, 'obshell_start', 'obshell_bootstrap')

    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients}, 'connect', 'seekdb_standby_detect')

    finally_plugins = ['display']
    if new_cluster_config:
        workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "new_cluster_config": new_cluster_config, "repository_dir": kwargs.get('repository').repository_dir}, "reload")
        cluster_config = new_cluster_config
    if new_clients:
        clients = new_clients

    workflow.add(const.STAGE_SECOND, 'obshell_client', 'obshell_health_check', 'obshell_dashboard')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "new_cluster_config": new_cluster_config, "cursor": None, "repository_dir": kwargs.get('repository').repository_dir}, *finally_plugins)

    return plugin_context.return_true()




