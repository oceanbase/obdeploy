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




def upgrade(plugin_context, stop_plugin, start_plugin, connect_plugin, display_plugin, *args, **kwargs):
    components = plugin_context.components
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    cmd = plugin_context.cmd
    options = plugin_context.options
    stdio = plugin_context.stdio
    local_home_path = kwargs.get('local_home_path')
    repository_dir = kwargs.get('repository_dir')
    
    zones_servers = {}
    for server in cluster_config.servers:
        config = cluster_config.get_server_conf(server)
        zone = config['zone']
        if zone not in zones_servers:
            zones_servers[zone] = []
        zones_servers[zone].append(server)
    
    all_servers = cluster_config.servers
    for zone in zones_servers:
        for server in zones_servers[zone]:
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config['home_path']
            remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
            remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
            client.execute_command("bash -c 'mkdir -p %s/{bin,lib}'" % (home_path))
            client.execute_command("ln -fs %s/bin/* %s/bin" % (remote_repository_dir, home_path))
            client.execute_command("ln -fs %s/lib/* %s/lib" % (remote_repository_dir, home_path))

        cluster_config.servers = zones_servers[zone]
        stdio.print('upgrade zone "%s"' % zone)
        if not stop_plugin(components, clients, cluster_config, cmd, options, stdio, *args, **kwargs):
            return 
        if not start_plugin(components, clients, cluster_config, cmd, options, stdio, *args, **kwargs):
            return 
    
    cluster_config.servers = all_servers
    ret = connect_plugin(components, clients, cluster_config, cmd, options, stdio, *args, **kwargs)
    if ret and display_plugin(components, clients, cluster_config, cmd, options, stdio, ret.get_return('cursor'), *args, **kwargs):
        return plugin_context.return_true()
