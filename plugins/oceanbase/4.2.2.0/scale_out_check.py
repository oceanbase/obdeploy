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
from const import COMP_OB, COMP_OB_CE
from copy import deepcopy


def add_plugin(component_name, plugins):
    if component_name not in plugins:
        plugins.append(component_name)


def scale_out_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    changed_components = cluster_config.get_deploy_changed_components()
    be_depend = cluster_config.be_depends
    plugins = []
    plugin_context.set_variable('need_bootstrap', False)
    need_restart = False
    if 'obagent' in added_components and 'obagent' in be_depend:
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
    if ('obproxy-ce' in added_components and 'obproxy-ce' in be_depend or 'obproxy' in added_components and 'obproxy' in be_depend):
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
    if 'ocp-express' in added_components and 'ocp-express' in be_depend:
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
        add_plugin('create_tenant', plugins)
    if 'ocp-server-ce' in added_components and 'ocp-server-ce' in be_depend:
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
        add_plugin('create_tenant', plugins)
    if 'oblogproxy' in added_components and 'oblogproxy' in be_depend:
        add_plugin('generate_config', plugins)
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
    if 'ob-configserver' in added_components:
        cluster_config.add_depend_component('ob-configserver')
    if cluster_config.added_servers:
        add_plugin('connect', plugins)
        add_plugin('bootstrap', plugins)
    if (COMP_OB_CE in added_components or COMP_OB in added_components) and not cluster_config.added_servers:
        plugin_context.set_variable('need_bootstrap', True)
        
    plugin_context.stdio.verbose('scale_out_check plugins: %s' % plugins)
    plugin_context.stdio.verbose('added_components: %s' % added_components)
    plugin_context.stdio.verbose('changed_components: %s' % changed_components)
    return plugin_context.return_true(plugins=plugins, need_restart=need_restart)
