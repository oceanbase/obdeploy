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


from __future__ import absolute_import, division, print_function

import const
from tool import ConfigUtil


def generate_random_password(cluster_config, auto_depend):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    be_depend = cluster_config.be_depends
    added_components = {
        component: component in add_components
        for component in const.COMPS_OB + const.COMPS_ODP + [const.COMP_OBAGENT, const.COMP_OBLOGPROXY]
    }
    be_depends = {
        component: (auto_depend or component in be_depend)
        for component in const.COMPS_ODP + [const.COMP_OBAGENT, const.COMP_OBLOGPROXY]
    }

    if added_components[cluster_config.name] and 'root_password' not in global_config:
        cluster_config.update_global_conf('root_password', ConfigUtil.get_random_pwd_by_total_length(20), False)

    if added_components[const.COMP_OBAGENT] and be_depends[const.COMP_OBAGENT] and 'ocp_agent_monitor_password' not in global_config:
        cluster_config.update_global_conf('ocp_agent_monitor_password', ConfigUtil.get_random_pwd_by_total_length(), False)

    if 'proxyro_password' not in global_config:
        for component_name in const.COMPS_ODP:
            if added_components[component_name] and be_depends[component_name]:
                cluster_config.update_global_conf('proxyro_password', ConfigUtil.get_random_pwd_by_total_length(), False)

    if added_components[const.COMP_OBLOGPROXY] and be_depends[const.COMP_OBLOGPROXY] and 'cdcro_password' not in global_config:
        cluster_config.update_global_conf('cdcro_password', ConfigUtil.get_random_pwd_by_total_length(), False)


def generate_config_pre(plugin_context, auto_depend=False, *args, **kwargs):

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
        'memory_limit', 'datafile_size', 'log_disk_size', 'system_memory', 'cpu_count', 'production_mode',
        'syslog_level', 'enable_syslog_wf', 'max_syslog_file_count', 'cluster_id', 'ocp_meta_tenant_log_disk_size',
        'datafile_next', 'datafile_maxsize'
    ]
    generate_password_keys = ['root_password', 'proxyro_password', 'ocp_meta_password', 'ocp_agent_monitor_password']
    generate_random_password_func_params = {
        'cluster_config': plugin_context.cluster_config,
        'auto_depend': auto_depend
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