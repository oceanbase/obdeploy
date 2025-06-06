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
from tool import get_option
from const import LOCATION_MODE

def dump_standby_relation(plugin_context, create_tenant_options=[], relation_tenants={}, cluster_configs={}, primary_tenant_info={}, *args, **kwargs):
    options = plugin_context.options
    log_source_type = getattr(options, 'type')
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    stdio = plugin_context.stdio
    if primary_tenant_info:
        primary_deploy_name = primary_tenant_info.get('primary_deploy_name')
        primary_tenant = primary_tenant_info.get('primary_tenant')
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    for options in multi_options:
        standby_tenant_name = get_option(options, 'tenant_name')
        if log_source_type == LOCATION_MODE:
            if not standby_tenant_name:
                standby_tenant_name = primary_tenant
            tenant_exists = plugin_context.get_variable(standby_tenant_name).get('tenant_exists')
            if not tenant_exists:
                deploy_name_tenants = deepcopy(relation_tenants)
                deploy_name_tenants.extend([[standby_deploy_name, standby_tenant_name], [primary_deploy_name, primary_tenant]])
                for deploy_name_tenant_tup in deploy_name_tenants:
                    relation_deploy_name = deploy_name_tenant_tup[0]
                    relation_tenant_name = deploy_name_tenant_tup[1]
                    for deploy_name_tenant_inner in deploy_name_tenants:
                        if (relation_deploy_name, relation_tenant_name) != tuple(deploy_name_tenant_inner):
                            _dump_standby_relation(relation_deploy_name, relation_tenant_name, deploy_name_tenant_inner, cluster_configs.get(relation_deploy_name), stdio)
                for cluster_config in cluster_configs.values():
                    cluster_config.update_component_attr('standby_relation', cluster_config.get_component_attr('standby_relation'), save=True)

        _dump_primary_tenant(standby_deploy_name, standby_tenant_name, primary_deploy_name, primary_tenant, cluster_configs.get(standby_deploy_name), stdio)
    
    return plugin_context.return_true()

def _dump_standby_relation(deploy_name, tenant_name, dump_relation_tenant, cluster_config, stdio):
    stdio.verbose('dump standby relation, deploy_name:{}, tenant_name:{},dump_relation_tenant:{}'.format(deploy_name, tenant_name, dump_relation_tenant))
    if not cluster_config:
        stdio.verbose('dump_standby_relation: No such deploy: %s.' % deploy_name)
        return False
    relation_dict = cluster_config.get_component_attr('standby_relation')
    if relation_dict:
        relation_tenants = relation_dict.get(tenant_name, [])
        if not relation_tenants:
            relation_dict[tenant_name] = [dump_relation_tenant]
        elif tuple(dump_relation_tenant) not in [tuple(t) for t in relation_tenants]:
            relation_tenants.append(dump_relation_tenant)
    else:
        relation_dict = {tenant_name: [dump_relation_tenant]}
    cluster_config.update_component_attr('standby_relation', relation_dict, save=False)
    return True

def _dump_primary_tenant(standby_deploy, standby_tenant_name, primary_deploy_name, primary_tenant, cluster_config, stdio):
    stdio.verbose('dump primary tenant info, standby_cluster:{}, standby_tenant:{}, primary_cluster:{}, primary_tenant:{}'.format(standby_deploy, standby_tenant_name, primary_deploy_name, primary_tenant))
    if not cluster_config:
        stdio.verbose('dump_primary_relation: No such deploy: %s.' % standby_deploy)
        return False
    
    primary_dict = cluster_config.get_component_attr('primary_tenant')
    if primary_dict:
        primary_dict[standby_tenant_name] = [[primary_deploy_name, primary_tenant]]
    else:
        primary_dict= {standby_tenant_name: [[primary_deploy_name, primary_tenant]]}
    cluster_config.update_component_attr('primary_tenant', primary_dict, save=True)
    return True