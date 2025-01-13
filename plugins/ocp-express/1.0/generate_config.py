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


def generate_config(plugin_context, auto_depend=False,  generate_config_mini=False, return_generate_keys=False, only_generate_password=False, *args, **kwargs):
    if return_generate_keys:
        generate_keys = plugin_context.get_variable('generate_keys')
        if not only_generate_password:
            generate_keys += ['memory_size', 'log_dir', 'logging_file_max_history']
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    generate_random_password = plugin_context.get_variable('generate_random_password')
    generate_random_password(cluster_config)
    if only_generate_password:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    depend_comps = [['obagent'], ['oceanbase', 'oceanbase-ce'], ['obproxy', 'obproxy-ce']]
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate ocp express configuration')
    min_memory_size = '752M'

    if auto_depend:
        for comps in depend_comps:
            for comp in comps:
                if comp in cluster_config.depends:
                    continue
                if cluster_config.add_depend_component(comp):
                    break
    global_config = cluster_config.get_global_conf()
    if generate_config_mini:
        if 'memory_size' not in global_config:
            cluster_config.update_global_conf('memory_size', min_memory_size, False)

    auto_set_memory = False
    if 'memory_size' not in global_config:
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            if 'memory_size' not in server_config:
                auto_set_memory = True
    if auto_set_memory:
        observer_num = 0
        for comp in ['oceanbase', 'oceanbase-ce']:
            if comp in cluster_config.depends:
                observer_num = len(cluster_config.get_depend_servers(comp))
        if not observer_num:
            stdio.warn('The component oceanbase/oceanbase-ce is not in the depends, the memory size cannot be calculated, and a fixed value of {} is used'.format(min_memory_size))
            cluster_config.update_global_conf('memory_size', min_memory_size, False)
        else:
            cluster_config.update_global_conf('memory_size', '%dM' % (512 + (observer_num + 3) * 60), False)

    stdio.stop_loading('succeed')
    plugin_context.return_true()
