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

    def __init__(self, plugin_context, local_home_path, start_check_plugin, start_plugin, reload_plugin, stop_plugin, connect_plugin,
                 display_plugin, repository, new_cluster_config=None, new_clients=None, bootstrap_plugin=None):
        self.local_home_path = local_home_path

        self.namespace = plugin_context.namespace
        self.namespaces = plugin_context.namespaces
        self.deploy_name = plugin_context.deploy_name
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
        self.start_check_plugin = start_check_plugin
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

    def dir_read_check(self, client, path):
        if not client.execute_command('cd %s' % path):
            dirpath, name = os.path.split(path)
            return self.dir_read_check(client, dirpath) and client.execute_command('sudo chmod +1 %s' % path)
        return True

    def restart(self):
        clients = self.clients

        if not self.call_plugin(self.stop_plugin):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False

        if self.new_clients:
            self.stdio.verbose('use new clients')
            for server in self.cluster_config.servers:
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                chown_cmd = 'sudo chown -R %s:' % new_client.config.username
                for key in ['home_path', 'storage']:
                    if key == 'storage':
                        storage_data = server_config.get(key, {})
                        database_type = storage_data.get('database_type')
                        connection_url = storage_data.get('connection_url')
                        if database_type == 'sqlite3' and connection_url:
                            sqlite_path = os.path.split(connection_url)[0]
                            if sqlite_path and sqlite_path != '/':
                                chown_cmd += sqlite_path
                    else:
                        chown_cmd += ' %s ' % server_config[key]
                if not new_client.execute_command(chown_cmd):
                    self.stdio.stop_loading('stop_loading', 'fail')
                    return False
                self.dir_read_check(new_client, server_config['home_path'])
            clients = self.new_clients

        cluster_config = self.new_cluster_config if self.new_cluster_config else self.cluster_config
        if not self.call_plugin(self.start_check_plugin, clients=clients, cluster_config=cluster_config):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False

        if not self.call_plugin(self.start_plugin, clients=clients, cluster_config=cluster_config,
                                need_bootstrap=False):
            self.rollback()
            self.stdio.stop_loading('stop_loading', 'fail')
            return False

        ret = self.call_plugin(self.connect_plugin, clients=clients, cluster_config=cluster_config)
        if ret:
            ret = self.call_plugin(self.display_plugin, clients=clients, cluster_config=cluster_config,
                                   cursor=ret.get_return('cursor'))
        return ret

    def rollback(self):
        if self.new_clients:
            self.stdio.start_loading('Rollback')
            cluster_config = self.new_cluster_config if self.new_cluster_config else self.cluster_config
            self.call_plugin(self.stop_plugin, clients=self.new_clients, cluster_config=cluster_config)
            for server in self.cluster_config.servers:
                client = self.clients[server]
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                chown_cmd = 'sudo chown -R %s:' % client.config.username
                for key in ['home_path']:
                    if key in server_config:
                        chown_cmd += ' %s' % server_config[key]
                new_client.execute_command(chown_cmd)
            self.stdio.stop_loading('succeed')


def restart(plugin_context, local_home_path, start_check_plugin, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin,
            new_cluster_config=None, new_clients=None, rollback=False, bootstrap_plugin=None, *args,
            **kwargs):
    repository = kwargs.get('repository')
    task = Restart(plugin_context, local_home_path, start_check_plugin, start_plugin, reload_plugin, stop_plugin, connect_plugin,
                   display_plugin, repository, new_cluster_config, new_clients)
    call = task.rollback if rollback else task.restart
    if call():
        plugin_context.return_true()
