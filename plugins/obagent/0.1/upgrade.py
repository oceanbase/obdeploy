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

import os


def call_plugin(plugin, plugin_context, repositories, *args, **kwargs):
    namespace = plugin_context.namespace
    namespaces = plugin_context.namespaces
    deploy_name = plugin_context.deploy_name
    deploy_status = plugin_context.deploy_status
    components = plugin_context.components
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    cmds = plugin_context.cmds
    options = plugin_context.options
    stdio = plugin_context.stdio
    return plugin(namespace, namespaces, deploy_name, deploy_status, repositories, components, clients, cluster_config, cmds, options,
        stdio, *args, **kwargs)


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, install_repository_to_servers, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients

    upgrade_ctx = kwargs.get('upgrade_ctx')
    local_home_path = kwargs.get('local_home_path')
    upgrade_repositories = kwargs.get('upgrade_repositories')

    cur_repository = upgrade_repositories[0]
    dest_repository = upgrade_repositories[-1]
    repository_dir = dest_repository.repository_dir
    kwargs['repository_dir'] = repository_dir

    stop_plugin = search_py_script_plugin([cur_repository], 'stop')[cur_repository]
    start_plugin = search_py_script_plugin([dest_repository], 'start')[dest_repository]
    connect_plugin = search_py_script_plugin([dest_repository], 'connect')[dest_repository]
    display_plugin = search_py_script_plugin([dest_repository], 'display')[dest_repository]

    apply_param_plugin(cur_repository)
    if not call_plugin(stop_plugin, plugin_context, [cur_repository], *args, **kwargs):
        return
    install_repository_to_servers(cluster_config.name, cluster_config, dest_repository, clients)

    apply_param_plugin(dest_repository)
    if not call_plugin(start_plugin, plugin_context, [dest_repository], *args, **kwargs):
        return

    ret = call_plugin(connect_plugin, plugin_context, [dest_repository], *args, **kwargs)
    if ret and call_plugin(display_plugin, plugin_context, [dest_repository], ret.get_return('cursor'), *args, **kwargs):
        upgrade_ctx['index'] = len(upgrade_repositories)
        return plugin_context.return_true()
