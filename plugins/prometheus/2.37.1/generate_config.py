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


def generate_config(plugin_context, auto_depend=False,  return_generate_keys=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if generate_password:
            generate_keys.append('basic_auth_users')
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    if generate_password:
        generate_random_password(cluster_config)
    if only_generate_password:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    have_depend = False
    depends = ['obagent']
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate prometheus configuration')

    for comp in cluster_config.depends:
        if comp in depends:
            have_depend = True

    if not have_depend and auto_depend:
        for depend in depends:
            if cluster_config.add_depend_component(depend):
                break
    if generate_password:
        generate_random_password(cluster_config)

    stdio.stop_loading('succeed')
    plugin_context.return_true()


def generate_random_password(cluster_config):
    global_config = cluster_config.get_original_global_conf()
    if 'basic_auth_users' not in global_config:
        cluster_config.update_global_conf('basic_auth_users', {'admin': ConfigUtil.get_random_pwd_by_total_length()})