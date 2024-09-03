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


def add_plugin(component_name, plugins):
    if component_name not in plugins:
        plugins.append(component_name)


def scale_out_check(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    plugins = []
    # check if obagents has changed
    if 'obagent' in cluster_config.depends:
        servers = cluster_config.get_depend_added_servers('obagent')
        if len(servers) != 0:
            return plugin_context.return_true(need_restart=True)
    if 'ocp-express' in added_components:
        plugin_context.set_variable('auto_depend', True)
        add_plugin('generate_config', plugins)
    return plugin_context.return_true(need_restart=False)
