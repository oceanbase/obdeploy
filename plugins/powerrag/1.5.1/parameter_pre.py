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

from optparse import Values

import const
from tool import set_plugin_context_variables


def parameter_pre(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf_with_default()

    tenants = []
    ob_config = None
    for comp in const.COMPS_OB:
        if comp in cluster_config.depends:
            ob_servers = cluster_config.get_depend_servers(comp)
            ob_config = cluster_config.get_depend_config(comp, ob_servers[0])
    if not ob_config:
        stdio.error('can not find oceanbase config')
        return plugin_context.return_false()

    options = dict()
    options['tenant_name'] = global_config.get('ob_tenant_name')
    options[global_config.get('ob_tenant_name') + '_root_password'] = global_config.get('ob_tenant_password') or ob_config.get('powerrag_tenant_password')
    tenants.append(Values(options))


    services = ['plugin_daemon', 'ssrf_proxy', 'sandbox', 'dify-api', 'powerrag', 'dify-worker', 'powerrag-worker']
    if global_config.get('enable_gpu') is True:
        services.append('ragflow-gpu')
    else:
        services.append('ragflow')

    env_map = {}
    first_start_services = {"plugin_daemon", "ssrf_proxy", "sandbox"}.intersection(set(services))
    second_start_services = {"dify-api", "ragflow-gpu", "ragflow", "powerrag"}.intersection(set(services))
    third_start_services = {"dify-worker", "powerrag-worker"}.intersection(set(services))
    variable_dict = {
        'env_map': env_map,
        'first_start_services': first_start_services,
        'second_start_services': second_start_services,
        'third_start_services': third_start_services
    }
    set_plugin_context_variables(plugin_context, variable_dict)
    return plugin_context.return_true(create_tenant_options=tenants)
