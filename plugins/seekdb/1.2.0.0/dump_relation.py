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

def dump_relation(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    deploy_manager = kwargs.get('deploy_manager')
    standby_cluster_config = plugin_context.cluster_config

    # Check if this is a standby cluster deployment
    primary_name = plugin_context.get_variable("primary_deploy_name")
    standby_name = plugin_context.cluster_config.deploy_name

    # Only proceed if both primary and standby are specified, which means we are deploying a standby cluster
    if not primary_name:
        return plugin_context.return_true()

    if primary_name == standby_name:
        stdio.verbose('primary_name is same as standby_name ({}), skipping dump_relation.'.format(primary_name))
        return plugin_context.return_true()

    stdio.verbose('Dumping standby relation for primary: {} and standby: {}'.format(primary_name, standby_name))

    primary_deploy = deploy_manager.get_deploy_config(primary_name)
    standby_deploy = deploy_manager.get_deploy_config(standby_name)

    if not primary_deploy:
        stdio.warn('Primary cluster {} not found while dumping relation.'.format(primary_name))
        return plugin_context.return_true()
    
    if not standby_deploy:
        stdio.warn('Standby cluster {} not found while dumping relation.'.format(standby_name))
        return plugin_context.return_true()
    
    # 1. Update Primary Cluster Config
    # Get the relation list directly (it's a list, not a dict)
    repository = kwargs.get('repository')
    primary_cluster_config = primary_deploy.deploy_config.components.get(repository.name)
    primary_relation_list = primary_cluster_config.get_component_attr('_cluster_standby_relation') or []
    
    # Add standby if not present (Primary config stores Standby names)
    if standby_name not in primary_relation_list:
        primary_relation_list.append(standby_name)
    
    # Update primary config
    primary_cluster_config.update_component_attr('_cluster_standby_relation', primary_relation_list, save=True)

    # 2. Update Standby Cluster Config
    # Standby config stores Primary names (usually just one, but list for consistency/future)
    
    standby_cluster_config.update_component_attr('_cluster_primary', primary_name, save=True)

    stdio.verbose('Successfully dumped standby relation.')
    return plugin_context.return_true()
