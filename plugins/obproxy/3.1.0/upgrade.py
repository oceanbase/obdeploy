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


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, *args, **kwargs):
    components = plugin_context.components
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    cmd = plugin_context.cmd
    options = plugin_context.options
    stdio = plugin_context.stdio

    upgrade_ctx = kwargs.get('upgrade_ctx')
    local_home_path = kwargs.get('local_home_path')
    upgrade_repositories = kwargs.get('upgrade_repositories')

    cur_repository = upgrade_repositories[0]
    dest_repository = upgrade_repositories[-1]
    repository_dir = dest_repository.repository_dir
    kwargs['repository_dir'] = repository_dir

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_home_path = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
        remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
        client.execute_command("bash -c 'mkdir -p %s/{bin,lib}'" % (home_path))
        client.execute_command("ln -fs %s/bin/* %s/bin" % (remote_repository_dir, home_path))
        client.execute_command("ln -fs %s/lib/* %s/lib" % (remote_repository_dir, home_path))

    stop_plugin = search_py_script_plugin([cur_repository], 'stop')[cur_repository]
    start_plugin = search_py_script_plugin([dest_repository], 'start')[dest_repository]
    connect_plugin = search_py_script_plugin([dest_repository], 'connect')[dest_repository]
    display_plugin = search_py_script_plugin([dest_repository], 'display')[dest_repository]
    bootstrap_plugin = search_py_script_plugin([dest_repository], 'bootstrap')[dest_repository]

    apply_param_plugin(cur_repository)
    if not stop_plugin(components, clients, cluster_config, cmd, options, stdio, *args, **kwargs):
        return 

    apply_param_plugin(dest_repository)
    if not start_plugin(components, clients, cluster_config, cmd, options, stdio, need_bootstrap=True, *args, **kwargs):
        return 
    
    ret = connect_plugin(components, clients, cluster_config, cmd, options, stdio, *args, **kwargs)
    if ret:
        if bootstrap_plugin(components, clients, cluster_config, cmd, options, stdio, ret.get_return('cursor'), *args, **kwargs) and display_plugin(components, clients, cluster_config, cmd, options, stdio, ret.get_return('cursor'), *args, **kwargs):
            upgrade_ctx['index'] = len(upgrade_repositories)
            return plugin_context.return_true()
