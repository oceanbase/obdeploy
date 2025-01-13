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
from _deploy import ClusterStatus


def restart(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.get_variable('clients')
    new_clients = plugin_context.get_variable('new_clients')
    new_deploy_config = plugin_context.get_variable('new_deploy_config')
    new_cluster_config = new_deploy_config.components[kwargs['repository'].name] if new_deploy_config else {}
    workflow.add(const.STAGE_FIRST - 1, 'connect')
    workflow.add_with_kwargs(const.STAGE_FIRST - 1, {'show_result': False}, 'get_binlog_instances')
    workflow.add_with_kwargs(const.STAGE_FIRST - 1, {'source_option': 'stop', 'no_instance_exit': False}, 'instance_manager')
    workflow.add(const.STAGE_FIRST, 'stop_pre')
    workflow.add_with_component(const.STAGE_FIRST, 'general', 'stop')
    if new_clients:
        workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {"new_clients": new_clients}, 'chown_dir')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config}, 'parameter_pre', 'cursor_check', 'start', 'health_check', 'connect')

    finally_plugins = ['display']
    if new_cluster_config:
        cluster_config = new_cluster_config
    if new_clients:
        clients = new_clients
    workflow.add_with_kwargs(const.STAGE_FIRST, {'target_status': ClusterStatus.STATUS_RUNNING}, 'status_check')
    workflow.add_with_kwargs(const.STAGE_FIRST, {'show_result': False}, 'get_binlog_instances')
    workflow.add_with_kwargs(const.STAGE_FIRST, {'source_option': 'start', 'no_instance_exit': False}, 'instance_manager')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "need_bootstrap": False}, *finally_plugins)

    return plugin_context.return_true()




