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

import time


def generate_password(plugin_context, return_generate_keys=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if not only_generate_password:
            generate_keys += plugin_context.get_variable('generate_base_keys')
        if generate_password:
            generate_keys += plugin_context.get_variable('generate_password_keys')
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    original_global_conf = cluster_config.get_original_global_conf()
    if not original_global_conf.get('appname'):
        cluster_config.update_global_conf('appname', plugin_context.deploy_name)
    if original_global_conf.get('cluster_id') is None:
        cluster_config.update_global_conf('cluster_id', round(time.time()) % 4294901759, False)
    if generate_password or only_generate_password:
        plugin_context.get_variable('generate_random_password')(**plugin_context.get_variable('generate_random_password_func_params'))
    return plugin_context.return_true()