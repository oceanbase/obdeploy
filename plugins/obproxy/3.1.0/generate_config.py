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

from collections import defaultdict

from tool import ConfigUtil


def generate_config(plugin_context, generate_config_mini=False, auto_depend=False, return_generate_keys=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if generate_password:
            generate_keys += ['obproxy_sys_password']
        if not only_generate_password:
            generate_keys += ['skip_proxy_sys_private_check', 'enable_strict_kernel_release', 'enable_cluster_checkout', 'proxy_mem_limited']
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    if generate_password:
        generate_random_password(cluster_config)
    if only_generate_password:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate obproxy configuration')

    global_config = cluster_config.get_original_global_conf()
    if 'skip_proxy_sys_private_check' not in global_config:
        generate_configs['global']['skip_proxy_sys_private_check'] = True
        cluster_config.update_global_conf('skip_proxy_sys_private_check', True, False)

    if 'enable_strict_kernel_release' not in global_config:
        generate_configs['global']['enable_strict_kernel_release'] = False
        cluster_config.update_global_conf('enable_strict_kernel_release', False, False)

    if 'enable_cluster_checkout' not in global_config:
        generate_configs['global']['enable_cluster_checkout'] = False
        cluster_config.update_global_conf('enable_cluster_checkout', False, False)

    if generate_config_mini:
        if 'proxy_mem_limited' not in global_config:
            generate_configs['global']['proxy_mem_limited'] = '500M'
            cluster_config.update_global_conf('proxy_mem_limited', '500M', False)

    # write required memory into resource namespace
    resource = plugin_context.namespace.get_variable("required_resource")
    if resource is None:
        resource = defaultdict(lambda: defaultdict(dict))
        plugin_context.namespace.set_variable("required_resource", resource)
    for server in cluster_config.servers:
        resource[cluster_config.name]['memory'][server.ip] = cluster_config.get_global_conf_with_default()['proxy_mem_limited']

    if auto_depend:
        for comp in ['oceanbase', 'oceanbase-ce', 'ob-configserver']:
            if comp in cluster_config.depends:
                continue
            if comp in plugin_context.components:
                cluster_config.add_depend_component(comp)


    stdio.stop_loading('succeed')
    return plugin_context.return_true()


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'obproxy_sys_password' not in global_config:
        cluster_config.update_global_conf('obproxy_sys_password', ConfigUtil.get_random_pwd_by_total_length(), False)
