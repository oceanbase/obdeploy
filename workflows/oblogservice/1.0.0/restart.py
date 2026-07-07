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
    clients = plugin_context.get_variable('clients') or plugin_context.clients
    new_clients = plugin_context.get_variable('new_clients')
    new_deploy_config = plugin_context.get_variable('new_deploy_config')
    new_cluster_config = None
    if new_deploy_config:
        new_cluster_config = new_deploy_config.components.get(kwargs['repository'].name)

    workflow.add(const.STAGE_FIRST, 'stop_pre')
    workflow.add_with_component(const.STAGE_FIRST, 'general', 'stop')

    start_cluster_config = new_cluster_config if new_cluster_config else cluster_config
    start_clients = new_clients if new_clients else clients
    workflow.add_with_kwargs(
        const.STAGE_FIRST,
        {
            'clients': start_clients,
            'cluster_config': start_cluster_config,
            'need_bootstrap': False,
        },
        'start_pre',
        'start',
        'health_check',
    )

    display_cluster_config = new_cluster_config if new_cluster_config else cluster_config
    display_clients = new_clients if new_clients else clients
    workflow.add_with_kwargs(
        const.STAGE_FIRST,
        {
            'clients': display_clients,
            'cluster_config': display_cluster_config,
            'need_bootstrap': False,
        },
        'display',
    )
    return plugin_context.return_true()
