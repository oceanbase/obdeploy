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

import const
from tool import ConfigUtil


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    be_depend = cluster_config.be_depends
    if cluster_config.name in add_components and 'root_password' not in global_config:
        cluster_config.update_global_conf('root_password', ConfigUtil.get_random_pwd_by_total_length(20), False)

    if 'proxyro_password' not in global_config:
        for component_name in const.COMPS_ODP:
            if component_name in add_components and component_name in be_depend:
                cluster_config.update_global_conf('proxyro_password', ConfigUtil.get_random_pwd_by_total_length(), False)


def generate_config_pre(plugin_context, *args, **kwargs):

    def update_server_conf(server, key, value):
        if server not in generate_configs:
            generate_configs[server] = {}
        generate_configs[server][key] = value

    def update_global_conf(key, value):
        generate_configs['global'][key] = value

    def summit_config():
        generate_global_config = generate_configs['global']
        for key in generate_global_config:
            stdio.verbose('Update global config %s to %s' % (key, generate_global_config[key]))
            cluster_config.update_global_conf(key, generate_global_config[key], False)
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_server_config = generate_configs[server]
            for key in generate_server_config:
                stdio.verbose('Update server %s config %s to %s' % (server, key, generate_server_config[key]))
                cluster_config.update_server_conf(server, key, generate_server_config[key], False)

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    generate_base_keys = [
        'memory_limit', 'datafile_size', 'clog_disk_utilization_threshold', 'clog_disk_usage_limit_percentage',
        'syslog_level', 'enable_syslog_wf', 'max_syslog_file_count', 'cluster_id', 'devname', 'system_memory', 'cpu_count'
    ]
    generate_password_keys = ['root_password', 'proxyro_password']
    generate_random_password_func_params = {
        'cluster_config': plugin_context.cluster_config
    }
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    plugin_context.set_variable('generate_base_keys', generate_base_keys)
    plugin_context.set_variable('generate_password_keys', generate_password_keys)
    plugin_context.set_variable('generate_random_password_func_params', generate_random_password_func_params)
    plugin_context.set_variable('generate_random_password', generate_random_password)
    plugin_context.set_variable('update_server_conf', update_server_conf)
    plugin_context.set_variable('update_global_conf', update_global_conf)
    plugin_context.set_variable('summit_config', summit_config)
    return plugin_context.return_true()