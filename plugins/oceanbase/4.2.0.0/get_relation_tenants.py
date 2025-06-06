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
from queue import Queue


def get_relation_tenants(plugin_context, repository, cluster_configs={}, *args, **kwargs):
    cmds = plugin_context.cmds
    options = plugin_context.options
    deploy_manager = kwargs.get('deploy_manager')
    get_deploy = deploy_manager.get_deploy_config
    deploy_name = plugin_context.cluster_config.deploy_name
    tenant_name = getattr(options, 'tenant_name', '')
    if kwargs.get('option_mode') == 'failover_decouple_tenant':
        deploy_name = cmds[0]
        tenant_name = cmds[1]
    if kwargs.get('option_mode') == 'create_standby_tenant':
        deploy_name = cmds[1]
        tenant_name = cmds[2]
    if kwargs.get('option_mode') in ['switchover_tenant', 'log_source']:
        deploy_name = cmds[0]
        tenant_name = cmds[1]
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