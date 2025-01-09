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

import _errno as err


def password_check(plugin_context, *args, **kwargs):
    alert = plugin_context.get_variable('alert')
    check_pass = plugin_context.get_variable('check_pass')
    cluster_config = plugin_context.cluster_config

    global_config = cluster_config.get_original_global_conf()
    key = 'observer_sys_password'
    for comp in ["oceanbase", "oceanbase-ce"]:
        if comp in cluster_config.depends:
            if key in global_config:
                alert(cluster_config.servers[0], 'password',
                    err.WC_PARAM_USELESS.format(key=key, current_comp=cluster_config.name, comp=comp),
                    [err.SUG_OB_SYS_PASSWORD.format()]
                )
            break
    for server in cluster_config.servers:
        check_pass(server, 'password')
    return plugin_context.return_true()