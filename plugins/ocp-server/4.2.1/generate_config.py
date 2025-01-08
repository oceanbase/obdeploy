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
from collections import defaultdict

from tool import ConfigUtil


def generate_config(plugin_context, auto_depend=False, generate_config_mini=False, return_generate_keys=False, *args, **kwargs):
    if return_generate_keys:
        return plugin_context.return_true(generate_keys=['memory_size', 'log_dir', 'logging_file_max_history', 'admin_password'])

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    depend_comps = [['obagent'], ['oceanbase', 'oceanbase-ce'], ['obproxy', 'obproxy-ce']]
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate ocp server configuration')
    min_memory_size = '2G'
    generate_random_password(cluster_config)

    if auto_depend:
        for comps in depend_comps:
            for comp in comps:
                if comp in cluster_config.depends:
                    continue
                if cluster_config.add_depend_component(comp):
                    break
    global_config = cluster_config.get_global_conf()
    if generate_config_mini:
        stdio.error('Deploying ocp-server is not supported in demo mode.')
        return plugin_context.return_false()

    if 'memory_size' not in global_config:
        cluster_config.update_global_conf('memory_size', min_memory_size, False)

    # write required memory into resource namespace
    resource = plugin_context.namespace.get_variable("required_resource")
    if resource is None:
        resource = defaultdict(lambda: defaultdict(dict))
        plugin_context.namespace.set_variable("required_resource", resource)
    for server in cluster_config.servers:
        resource[cluster_config.name]['memory'][server.ip] = cluster_config.get_global_conf_with_default()['memory_size']
    stdio.stop_loading('succeed')
    return plugin_context.return_true()


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'admin_password' not in global_config:
        cluster_config.update_global_conf('admin_password', ConfigUtil.get_random_pwd_by_rule(punctuation_length=2, punctuation_chars='~^*{}[]_-+'), False)