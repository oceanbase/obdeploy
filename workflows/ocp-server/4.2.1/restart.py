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
    workflow.add(const.STAGE_FIRST, 'stop_pre')
    workflow.add_with_component(const.STAGE_FIRST, 'general', 'stop')
    if new_clients:
        workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {'new_clients': new_clients}, 'chown_dir')
    need_bootstrap = plugin_context.get_variable('need_bootstrap') and True
    cursor = plugin_context.get_return('connect').get_return('cursor')
    if not plugin_context.cluster_config.depends:
        workflow.add_with_kwargs(const.STAGE_FIRST, {'need_connect': False}, 'cursor_check')
    workflow.add_with_kwargs(const.STAGE_FIRST, {'cursor': cursor if cursor else None, 'need_bootstrap': need_bootstrap,
                                                 'clients': new_clients if new_clients else clients, 'new_cluster_config': new_cluster_config,
                                                 'cluster_config': new_cluster_config if new_cluster_config else cluster_config}, 'parameter_pre', 'ocp_const', 'start', 'health_check')

    finally_plugins = plugin_context.get_variable('finally_plugins')
    if not finally_plugins:
        finally_plugins = ['connect', 'display']
        if need_bootstrap:
            finally_plugins.insert(1, 'bootstrap')
    if new_cluster_config:
        cluster_config = new_cluster_config
    if new_clients:
        clients = new_clients

    workflow.add_with_kwargs(const.STAGE_FIRST, {'clients': clients, 'cluster_config': cluster_config, 'need_bootstrap': True}, *finally_plugins)

    return plugin_context.return_true()




