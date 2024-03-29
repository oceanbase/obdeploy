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

from queue import Queue


def get_relation_tenants(plugin_context, repository, get_deploy, deployment_name='', tenant_name='', cluster_configs={}, *args, **kwargs):
    deploy_name = deployment_name if deployment_name else plugin_context.cluster_config.deploy_name
    options = plugin_context.options
    tenant_name = tenant_name if tenant_name else getattr(options, 'tenant_name', '')
    stdio = plugin_context.stdio
    visited_deployname_set = set()
    queue = Queue()
    queue.put((deploy_name, tenant_name))
    deploy_name_tenant = set()
    relation_deploy_names = set()
    all_tenant_names = set()
    while not queue.empty():
        relation_kv = queue.get()
        relation_deploy_name = relation_kv[0]
        if relation_deploy_name in visited_deployname_set:
            continue
        visited_deployname_set.add(relation_deploy_name)
        deploy = get_deploy(relation_deploy_name)
        if not deploy:
            stdio.verbose('No such deploy: %s.' % relation_deploy_name)
            continue
        cluster_config = deploy.deploy_config.components.get(repository.name)
        if not cluster_config:
            stdio.verbose('No such OceanBase in : %s.' % relation_deploy_name)
            continue
        cluster_configs[relation_deploy_name] = cluster_config
        relation_dict = cluster_config.get_component_attr('standby_relation')
        if relation_dict:
            for tenant in relation_dict:
                if relation_deploy_name == deploy_name:
                    all_tenant_names.add(tenant)
                if tenant_name and tenant != tenant_name:
                    continue
                deploy_name_tenant.add((relation_deploy_name, tenant))
                relation_arr = relation_dict[tenant]
                for relation_kv in relation_arr:
                    re_deploy_name = relation_kv[0]
                    deploy_name_tenant.add((re_deploy_name, relation_kv[1]))
                    relation_deploy_names.add(re_deploy_name)
                    queue.put(relation_kv)
                    if re_deploy_name not in cluster_configs:
                        deploy = get_deploy(re_deploy_name)
                        if not deploy:
                            continue
                        cluster_config = deploy.deploy_config.components[repository.name]
                        cluster_configs[re_deploy_name] = cluster_config

    plugin_context.set_variable('relation_tenants', list(deploy_name_tenant))
    plugin_context.set_variable('relation_deploy_names', list(relation_deploy_names))
    plugin_context.set_variable('all_tenant_names', list(all_tenant_names))
    plugin_context.set_variable('cluster_configs', cluster_configs)
    return plugin_context.return_true()