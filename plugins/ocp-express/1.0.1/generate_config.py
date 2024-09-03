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

import re

from tool import ConfigUtil


def generate_config(plugin_context, auto_depend=False, generate_config_mini=False, return_generate_keys=False, only_generate_password=False, *args, **kwargs):
    if return_generate_keys:
        generate_keys = ['admin_passwd']
        if not only_generate_password:
            generate_keys += ['memory_size', 'log_dir', 'logging_file_max_history']
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
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


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'admin_passwd' not in global_config:
        cluster_config.update_global_conf('admin_passwd', ConfigUtil.get_random_pwd_by_rule(), False)
    if cluster_config.name in add_components and 'oceanbase-ce' not in add_components and 'oceanbase' not in add_components and 'ocp_root_password' not in global_config:
        cluster_config.update_global_conf('ocp_root_password', ConfigUtil.get_random_pwd_by_rule(), False)

