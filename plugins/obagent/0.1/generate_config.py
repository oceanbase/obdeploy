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

from tool import ConfigUtil


def generate_config(plugin_context, auto_depend=False, return_generate_keys=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if generate_password:
            generate_keys += ['http_basic_auth_password']
        if not only_generate_password:
            generate_keys += ['ob_monitor_status']
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    if generate_password:
        generate_random_password(cluster_config)
    if only_generate_password:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    have_depend = False
    depends = ['oceanbase', 'oceanbase-ce']
    server_depends = {}
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate obagent configuration')

    for comp in cluster_config.depends:
        if comp in depends:
            have_depend = True
            for server in cluster_config.servers:
                server_depends[server] = []
                obs_config = cluster_config.get_depend_config(comp, server)
                if obs_config is not None:
                    server_depends[server].append(comp)

    if have_depend:
        for server in cluster_config.servers:
            for comp in depends:
                if comp in server_depends[server]:
                    break
            else:
                cluster_config.update_server_conf(server, 'ob_monitor_status', 'inactive', False)
                if generate_configs.get(server) is None:
                    generate_configs[server] = {}
                generate_configs[server]['ob_monitor_status'] = 'inactive'
    else:
        cluster_config.update_global_conf('ob_monitor_status', 'inactive', False)
        generate_configs['global']['ob_monitor_status'] = 'inactive'
        if auto_depend:
            for depend in depends:
                if cluster_config.add_depend_component(depend):
                    cluster_config.update_global_conf('ob_monitor_status', 'active', False)
                    generate_configs['global']['ob_monitor_status'] = 'active'
                    break

    stdio.stop_loading('succeed')
    plugin_context.return_true()


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'http_basic_auth_password' not in global_config:
        cluster_config.update_global_conf('http_basic_auth_password', ConfigUtil.get_random_pwd_by_rule(lowercase_length=3, uppercase_length=3, digits_length=3, punctuation_length=0), save=False)
