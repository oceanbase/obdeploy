
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

    def __init__(self, plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config=None, new_clients=None, bootstrap_plugin=None):
        self.local_home_path = local_home_path

        self.namespace = plugin_context.namespace
        self.namespaces = plugin_context.namespaces
        self.deploy_name = plugin_context.deploy_name
        self.deploy_status = plugin_context.deploy_status
        self.repositories = plugin_context.repositories
        self.plugin_name = plugin_context.plugin_name

        self.components = plugin_context.components
        self.clients = plugin_context.clients
        self.cluster_config = plugin_context.cluster_config
        self.cmds = plugin_context.cmds
        self.options = plugin_context.options
        self.dev_mode = plugin_context.dev_mode
        self.stdio = plugin_context.stdio

        self.plugin_context = plugin_context
        self.repository = repository
        self.start_plugin = start_plugin
        self.reload_plugin = reload_plugin
        self.connect_plugin = connect_plugin
        self.display_plugin = display_plugin
        self.bootstrap_plugin = bootstrap_plugin
        self.stop_plugin = stop_plugin
        self.new_clients = new_clients
        self.new_cluster_config = new_cluster_config
        self.sub_io = self.stdio.sub_io()
        self.dbs = None
        self.cursors = None
    
    def call_plugin(self, plugin, **kwargs):
        args = {
            'namespace': self.namespace,
            'namespaces': self.namespaces,
            'deploy_name': self.deploy_name,
            'deploy_status': self.deploy_status,
            'cluster_config': self.cluster_config,
            'repositories': self.repositories,
            'repository': self.repository,
            'components': self.components,
            'clients': self.clients,
            'cmd': self.cmds,
            'options': self.options,
            'stdio': self.sub_io
        }
        args.update(kwargs)
        
        self.stdio.verbose('Call %s for %s' % (plugin, self.repository))
        return plugin(**args)

    def connect(self, cluster_config):
        self.sub_io.start_loading('Connect to obproxy')
        ret = self.call_plugin(self.connect_plugin, cluster_config=cluster_config)
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
        if self.new_cluster_config:
            if not self.connect(self.cluster_config):
                return False
            self.call_plugin(self.reload_plugin, clients=clients, cursor=self.cursors, new_cluster_config=self.new_cluster_config)

        if not self.call_plugin(self.stop_plugin, clients=clients):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        
        if self.new_clients:
            self.stdio.verbose('use new clients')
            for server in self.cluster_config.servers:
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                home_path = server_config['home_path']
                if not new_client.execute_command('sudo chown -R %s: %s' % (new_client.config.username, home_path)):
                    self.stdio.stop_loading('stop_loading', 'fail')
                    return False
                self.dir_read_check(new_client, home_path)
            clients = self.new_clients

        cluster_config = self.new_cluster_config if self.new_cluster_config else self.cluster_config
        need_bootstrap = self.bootstrap_plugin is not None
        if not self.call_plugin(self.start_plugin, clients=clients, cluster_config=cluster_config, local_home_path=self.local_home_path, repository=self.repository):
            self.rollback()
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        
        if self.connect(cluster_config):
            if self.bootstrap_plugin:
                self.call_plugin(self.bootstrap_plugin, cluster_config=cluster_config, cursor=self.cursors)
            return self.call_plugin(self.display_plugin, cluster_config=cluster_config, cursor=self.cursors) if self.display_plugin else True
        return False

    def rollback(self):
        if self.new_clients:
            cluster_config = self.new_cluster_config if self.new_cluster_config else self.cluster_config
            self.call_plugin(self.stop_plugin, clients=self.new_clients, cluster_config=cluster_config)
            for server in self.cluster_config.servers:
                client = self.clients[server]
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                home_path = server_config['home_path']
                new_client.execute_command('sudo chown -R %s: %s' % (client.config.username, home_path))


def restart(plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, new_cluster_config=None, new_clients=None, rollback=False, bootstrap_plugin=None, *args, **kwargs):
    repository = kwargs.get('repository')
    task = Restart(plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config, new_clients, bootstrap_plugin=bootstrap_plugin)
    call = task.rollback if rollback else task.restart
    if call():
        plugin_context.return_true()
