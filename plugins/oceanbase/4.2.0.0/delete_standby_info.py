# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.
from copy import deepcopy


def delete_relation_in_inner_config(cluster_config, tenant_name, cluster_config_deleted, tenant_name_deleted, stdio):
    relation_tenant_deleted = [cluster_config_deleted, tenant_name_deleted]
    relation_dict = cluster_config.get_component_attr('standby_relation')
    if relation_dict:
        if tenant_name not in relation_dict:
            stdio.verbose('skip delete relation: {} does not have relation'.format(tenant_name))
            return
        relation_arr = relation_dict.get(tenant_name, [])
        if tenant_name_deleted:
            for relation_kv in relation_arr:
                if list(relation_kv) == relation_tenant_deleted:
                    relation_arr.remove(relation_kv)
                    break
            if len(relation_arr) == 0:
                del relation_dict[tenant_name]
        else:
            del relation_dict[tenant_name]
        cluster_config.update_component_attr('standby_relation', relation_dict if relation_dict else {}, save=False)
        
        
def delete_standbyro_password(deploy_name, tenant_name, cluster_config, stdio):
    if not cluster_config:
        stdio.error('No such deploy: %s.' % deploy_name)
    else:
        standbyro_password_dict = cluster_config.get_component_attr('standbyro_password')
        if standbyro_password_dict:
            if tenant_name in standbyro_password_dict:
                standbyro_password_dict.pop(tenant_name)
                cluster_config.update_component_attr('standbyro_password', standbyro_password_dict, save=False)


def delete_standby_info(plugin_context, cluster_configs={}, delete_password=True, *args, **kwargs):
    stdio = plugin_context.stdio
    if not cluster_configs:
        stdio.verbose('no cluster_configs found, skip delete standby relationship.')
        return plugin_context.return_true()
    options = plugin_context.options
    tenant_name = getattr(options, 'tenant_name', '')
    cluster_config = plugin_context.cluster_config
    deploy_name = plugin_context.deploy_name
    standby_relation = deepcopy(cluster_config.get_component_attr('standby_relation'))
    standbyro_password = deepcopy(cluster_config.get_component_attr('standbyro_password'))
    option_type = plugin_context.get_variable('option_type')
    relation_tenants = plugin_context.get_variable('relation_tenants')

    # if option_type is 'failover' or 'decouple', can not delete relationship , because there are multiple relationships
    if option_type in ['failover', 'decouple'] and len(relation_tenants) > 2:
        stdio.verbose('The current operation is {}, and it is unable to determine multiple primary-standby relationships, skip delete relationship.'.format(option_type))
        return plugin_context.return_true()
    
    if delete_password and standbyro_password:
        for inner_tenant_name in standbyro_password:
            if tenant_name and tenant_name != inner_tenant_name:
                continue
            delete_standbyro_password(deploy_name, inner_tenant_name, cluster_config, plugin_context.stdio)

    if standby_relation:
        for inner_tenant_name in standby_relation:
            relation_arr = standby_relation[inner_tenant_name]
            if tenant_name and tenant_name != inner_tenant_name:
                continue
            for relation_kv in relation_arr:
                relation_deploy_name = relation_kv[0]
                relation_tenant = relation_kv[1]
                relation_cluster_config = plugin_context.get_variable('cluster_configs').get(relation_deploy_name)
                if not relation_cluster_config:
                    continue
                delete_relation_in_inner_config(relation_cluster_config, relation_tenant, deploy_name, inner_tenant_name, stdio)
            delete_relation_in_inner_config(cluster_config, inner_tenant_name, deploy_name, '', stdio)
    # dump
    for deployment_name in plugin_context.get_variable('cluster_configs'):
        cluster_config = cluster_configs[deployment_name]
        if not cluster_config.update_component_attr('standby_relation', cluster_config.get_component_attr('standby_relation'), save=True):
            stdio.warn('delete standby_relation failed, deployment_name: {}'.format(deployment_name))
        if not cluster_config.update_component_attr('standbyro_password', cluster_config.get_component_attr('standbyro_password'), save=True):
            stdio.warn('delete standbyro_password failed, deployment_name: {}'.format(deployment_name))


    return plugin_context.return_true()