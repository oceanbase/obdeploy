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

def switchover_primary_tenant_info(plugin_context, cluster_configs, primary_info={}, *args, **kwargs):
    cmds = plugin_context.cmds
    stdio = plugin_context.stdio
    
    new_primary_cluster = plugin_context.cluster_config.deploy_name
    new_primary_tenant = cmds[1]
    new_standby_cluster = primary_info.get('primary_deploy_name')
    new_standby_tenant = primary_info.get('primary_tenant')

    old_primary_standby_tenants = plugin_context.get_variable('old_primary_standby_tenants')
    old_standby_standby_tenants = plugin_context.get_variable('old_standby_standby_tenants')

    stdio.start_loading("switchover primary tenant info")

    # Delete the primary_tenant information from the old backup
    cluster_config = cluster_configs.get(new_primary_cluster)
    primary_dict = cluster_config.get_component_attr('primary_tenant')
    if primary_dict:
        primary_info = primary_dict.get(new_primary_tenant, [])
        if primary_info:
            del primary_dict[new_primary_tenant]
        cluster_config.update_component_attr('primary_tenant', primary_dict if primary_dict else {}, save=True)
    
    # Add the primary_tenant information to the new backup
    cluster_config = cluster_configs.get(new_standby_cluster)
    primary_dict = cluster_config.get_component_attr('primary_tenant')
    if primary_dict:
        primary_dict[new_standby_tenant] = [[new_primary_cluster, new_primary_tenant]]
    else:
        primary_dict = {new_standby_tenant: [[new_primary_cluster, new_primary_tenant]]}
    cluster_config.update_component_attr('primary_tenant', primary_dict, save=True)

    for tenant_info in old_primary_standby_tenants:
        deploy_name = tenant_info[0]
        tenant_name = tenant_info[1]

        stdio.verbose("set {}:{}'s standby tenants:{} as standby tenants of the tenant {}:{}".format(new_standby_cluster, new_standby_tenant, tenant_name, new_primary_cluster, new_primary_tenant))
        cluster_config = cluster_configs.get(deploy_name)
        primary_dict = cluster_config.get_component_attr('primary_tenant')
        if primary_dict:
            primary_dict[tenant_name] = [[new_primary_cluster, new_primary_tenant]]
        else:
            primary_dict = {tenant_name: [[new_primary_cluster, new_primary_tenant]]}
        cluster_config.update_component_attr('primary_tenant', primary_dict, save=True)

    for tenant_info in old_standby_standby_tenants:
        deploy_name = tenant_info[0]
        tenant_name = tenant_info[1]
        stdio.verbose("set {}:{}'s standby tenants:{} as standby tenants of the tenant {}:{}".format(new_primary_cluster, new_primary_tenant, tenant_name, new_standby_cluster, new_standby_tenant))
        cluster_config = cluster_configs.get(deploy_name)
        primary_dict = cluster_config.get_component_attr('primary_tenant')
        if primary_dict:
            primary_dict[tenant_name] = [[new_standby_cluster, new_standby_tenant]]
        else:
            primary_dict = {tenant_name: [[new_standby_cluster, new_standby_tenant]]}
        cluster_config.update_component_attr('primary_tenant', primary_dict, save=True)

    stdio.stop_loading('succeed')
    stdio.print('You can use the command "obd cluster tenant show {} -g" to view the relationship between the primary and standby tenants.'.format(new_primary_cluster))
    return plugin_context.return_true()
