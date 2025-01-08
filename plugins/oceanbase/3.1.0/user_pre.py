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

from optparse import Values

import const


def user_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    added_components = cluster_config.get_deploy_added_components()
    changed_components = cluster_config.get_deploy_changed_components()
    stdio.verbose('bootstrap for components: %s' % added_components)
    stdio.verbose('scale out for components: %s' % changed_components)
    global_conf = cluster_config.get_global_conf()
    be_depend = cluster_config.be_depends

    user_infos = []
    has_obproxy = False
    has_obproxy_scale_out = False
    for component_name in ['obproxy', 'obproxy-ce']:
        if component_name in added_components and component_name in be_depend:
            has_obproxy = True
            break
        if component_name in changed_components:
            has_obproxy_scale_out = True
            break
    if has_obproxy or ('proxyro_password' in global_conf and not has_obproxy_scale_out):
        user_info = {}
        user_info['db_username'] = global_conf.get('proxyro', 'proxyro')
        user_info['db_password'] = global_conf.get('proxyro_password', '')
        user_infos.append(Values(user_info))

    has_obagent = "obagent" in added_components and "obagent" in be_depend
    if has_obagent or ('ocp_agent_monitor_password' in global_conf and 'obagent' not in changed_components):
        user_info = {}
        user_info['db_username'] = cluster_config.get_global_conf_with_default().get('ocp_agent_monitor_username')
        user_info['db_password'] = global_conf.get('ocp_agent_monitor_password','')
        user_infos.append(Values(user_info))

    plugin_context.set_variable("create_tenant_options", user_infos)
    return plugin_context.return_true()
