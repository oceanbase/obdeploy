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



def change_repo(plugin_context, local_home_path, repository, *args, **kwargs):
    components = plugin_context.components
    cluster_config = plugin_context.cluster_config
    repository_dir = repository.repository_dir
    options = plugin_context.options
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    global_ret = True

    stdio.start_loading('Change repository')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_home_path = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
        remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
        global_ret = client.execute_command("bash -c 'mkdir -p %s/{bin,lib}'" % (home_path)) and global_ret
        global_ret = client.execute_command("ln -fs %s/bin/* %s/bin" % (remote_repository_dir, home_path)) and global_ret
        global_ret = client.execute_command("ln -fs %s/lib/* %s/lib" % (remote_repository_dir, home_path)) and global_ret
    
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('failed')