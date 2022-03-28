
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


class Restart(object):

    def __init__(self, plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config=None, new_clients=None):
        self.local_home_path = local_home_path
        self.plugin_context = plugin_context
        self.components = plugin_context.components
        self.clients = plugin_context.clients
        self.cluster_config = plugin_context.cluster_config
        self.stdio = plugin_context.stdio
        self.repository = repository
        self.start_plugin = start_plugin
        self.reload_plugin = reload_plugin
        self.connect_plugin = connect_plugin
        self.display_plugin = display_plugin
        self.stop_plugin = stop_plugin
        self.new_clients = new_clients
        self.new_cluster_config = new_cluster_config
        self.sub_io = self.stdio.sub_io()
        self.dbs = None
        self.cursors = None

    # def close(self):
    #     if self.dbs:
    #         for server in self.cursors:
    #             self.cursors[server].close()
    #         for db in self.dbs:
    #             self.dbs[server].close()
    #         self.cursors = None
    #         self.dbs = None

    def connect(self):
        if self.cursors is None:
            self.stdio.verbose('Call %s for %s' % (self.connect_plugin, self.repository))
            self.sub_io.start_loading('Connect to obproxy')
            ret = self.connect_plugin(self.components, self.clients, self.cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io)
            if not ret:
                self.sub_io.stop_loading('fail')
                return False
            self.sub_io.stop_loading('succeed')
            # self.close()
            self.cursors = ret.get_return('cursor')
            self.dbs = ret.get_return('connect')
        return True

    def dir_read_check(self, client, path):
        if not client.execute_command('cd %s' % path):
            dirpath, name = os.path.split(path)
            return self.dir_read_check(client, dirpath) and client.execute_command('sudo chmod +1 %s' % path)
        return True

    def restart(self):
        clients = self.clients
        self.stdio.verbose('Call %s for %s' % (self.stop_plugin, self.repository))
        if not self.stop_plugin(self.components, clients, self.cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        
        if self.new_clients:
            self.stdio.verbose('use new clients')
            for server in self.cluster_config.servers:
                client = clients[server]
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                home_path = server_config['home_path']
                if not new_client.execute_command('sudo chown -R %s: %s' % (new_client.config.username, home_path)):
                    self.stdio.stop_loading('stop_loading', 'fail')
                    return False
                self.dir_read_check(new_client, home_path)
            clients = self.new_clients

        cluster_config = self.new_cluster_config if self.new_cluster_config else self.cluster_config
        self.stdio.verbose('Call %s for %s' % (self.start_plugin, self.repository))
        if not self.start_plugin(self.components, clients, cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io, local_home_path=self.local_home_path, repository_dir=self.repository.repository_dir):
            self.rollback()
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        
        if self.connect():
            ret = self.display_plugin(self.components, clients, cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io, cursor=self.cursors)
            if self.new_cluster_config:
                self.stdio.verbose('Call %s for %s' % (self.reload_plugin, self.repository))
                self.reload_plugin(self.components, self.clients, self.cluster_config, [], {}, self.sub_io, 
                cursor=self.cursors, new_cluster_config=self.new_cluster_config, repository_dir=self.repository.repository_dir)
            return ret
        return False

    def rollback(self):
        if self.new_clients:
            self.stop_plugin(self.components, self.new_clients, self.new_cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io)
            for server in self.cluster_config.servers:
                client = self.clients[server]
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                home_path = server_config['home_path']
                new_client.execute_command('sudo chown -R %s: %s' % (client.config.username, home_path))


def restart(plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config=None, new_clients=None, rollback=False, *args, **kwargs):
    task = Restart(plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config, new_clients)
    call = task.rollback if rollback else task.restart
    if call():
        plugin_context.return_true()
