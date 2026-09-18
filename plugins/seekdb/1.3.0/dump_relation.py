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

from copy import deepcopy


def dump_relation(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    deploy_manager = kwargs.get('deploy_manager')
    standby_cluster_config = plugin_context.cluster_config

    requested_primary_name = plugin_context.get_variable('primary_deploy_name')
    persisted_primary_name = standby_cluster_config.get_component_attr('_cluster_primary')
    primary_name = requested_primary_name or persisted_primary_name
    standby_name = standby_cluster_config.deploy_name

    if not primary_name:
        return plugin_context.return_true()
    if primary_name == standby_name:
        stdio.verbose(
            'primary_name is same as standby_name ({}), skipping dump_relation.'.format(
                primary_name))
        return plugin_context.return_true()

    primary_deploy = deploy_manager.get_deploy_config(primary_name)
    standby_deploy = deploy_manager.get_deploy_config(standby_name)
    if not primary_deploy:
        stdio.warn(
            'Primary cluster {} not found while dumping relation.'.format(primary_name))
        return plugin_context.return_true()
    if not standby_deploy:
        stdio.warn(
            'Standby cluster {} not found while dumping relation.'.format(standby_name))
        return plugin_context.return_true()

    repository = kwargs.get('repository')
    primary_cluster_config = primary_deploy.deploy_config.components.get(repository.name)
    primary_relation_list = deepcopy(
        primary_cluster_config.get_component_attr('_cluster_standby_relation') or [])

    # Persist the retry marker before touching the primary deployment. If the
    # second write fails, an ordinary 1.3/1.4 start can finish the transaction.
    sync_pending = standby_cluster_config.get_component_attr(
        '_obshell_standby_sync_pending')
    if requested_primary_name or sync_pending or persisted_primary_name != primary_name:
        if not standby_cluster_config.update_component_attrs({
                '_cluster_primary': primary_name,
                '_obshell_standby_sync_pending': True,
        }, save=True):
            stdio.error('Failed to persist the standby primary relation.')
            return plugin_context.return_false()

    if standby_name not in primary_relation_list:
        primary_relation_list.append(standby_name)
        if not primary_cluster_config.update_component_attr(
                '_cluster_standby_relation', primary_relation_list, save=True):
            stdio.error('Failed to persist the primary standby relation.')
            return plugin_context.return_false()

    stdio.verbose('Successfully dumped standby relation.')
    return plugin_context.return_true()
