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
import time


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
        self.stop_plugin = stop_plugin
        self.display_plugin = display_plugin
        self.new_clients = new_clients
        self.new_cluster_config = new_cluster_config
        self.now_clients = {}
        self.sub_io = self.stdio.sub_io()
        self.db = None
        self.cursor = None
        for server in self.cluster_config.servers:
            self.now_clients[server] = self.clients[server]

    def close(self):
        if self.db:
            self.cursor.close()
            self.db.close()
            self.cursor = None
            self.db = None

    def connect(self):
        if self.cursor is None or self.execute_sql('select version()', error=False) is False:
            self.stdio.verbose('Call %s for %s' % (self.connect_plugin, self.repository))
            self.sub_io.start_loading('Connect to observer')
            ret = self.connect_plugin(self.components, self.clients, self.cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io)
            if not ret:
                self.sub_io.stop_loading('fail')
                return False
            self.sub_io.stop_loading('succeed')
            self.close()
            self.cursor = ret.get_return('cursor')
            self.db = ret.get_return('connect')
            while self.execute_sql('use oceanbase', error=False) is False:
                time.sleep(2)
            self.execute_sql('set session ob_query_timeout=1000000000')
        return True

    def execute_sql(self, query, args=None, one=True, error=True):
        msg = query % tuple(args) if args is not None else query
        self.stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            self.stdio.verbose('execute sql: %s' % msg)
            self.cursor.execute(query, args)
            result = self.cursor.fetchone() if one else self.cursor.fetchall()
            result and self.stdio.verbose(result)
            return result
        except:
            msg = 'execute sql exception: %s' % msg if error else ''
            self.stdio.exception(msg)
        return False

    def broken_sql(self, sql, sleep_time=3):
        while True:
            ret = self.execute_sql(sql, error=False)
            if ret is None:
                break
            time.sleep(sleep_time)

    def wait(self):
        if not self.connect():
            return False
        self.stdio.verbose('server cneck')
        self.broken_sql("select * from oceanbase.__all_server where status != 'active' or stop_time > 0 or start_service_time = 0")
        self.broken_sql("select * from oceanbase.__all_virtual_clog_stat where is_in_sync= 0 and is_offline = 0")
        return True

    def start_zone(self, zone=None):
        if not self.connect():
            return False
        if zone:
            self.stdio.verbose('start zone %s' % zone)
            start_sql = "alter system start zone %s" % zone
            check_sql = "select * from oceanbase.__all_zone where name = 'status' and zone = '%s' and info != 'ACTIVE'" % zone
            while True:
                if self.execute_sql(start_sql, error=False) is None:
                    break
                if self.execute_sql(check_sql, error=False) is None:
                    break
                time.sleep(3)
        self.wait()
        return True

    def stop_zone(self, zone):
        if not self.wait():
            return False

        self.stdio.verbose('stop zone %s' % zone)
        stop_sql = "alter system stop zone %s" % zone
        check_sql = "select * from oceanbase.__all_zone where name = 'status' and zone = '%s' and info = 'ACTIVE'" % zone
        while True:
            if self.execute_sql(stop_sql, error=False) is None:
                break
            if self.execute_sql(check_sql, error=False):
                break
            time.sleep(3)
        return True

    def rollback(self):
        if self.new_clients:
            self.stdio.start_loading('Rollback')
            self.stop_plugin(self.components, self.now_clients, self.new_cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io)
            for server in self.cluster_config.servers:
                client = self.clients[server]
                new_client = self.now_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                home_path = server_config['home_path']
                chown_cmd = 'sudo chown -R %s:' % client.config.username
                for key in ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']:
                    if key in server_config:
                        chown_cmd += ' %s' % server_config[key]
                new_client.execute_command(chown_cmd)
            self.stdio.stop_loading('succeed')

    def dir_read_check(self, client, path):
        if not client.execute_command('cd %s' % path):
            dirpath, name = os.path.split(path)
            return self.dir_read_check(client, dirpath) and client.execute_command('sudo chmod +1 %s' % path)
        return True

    def _restart(self):
        clients = self.clients
        self.stdio.verbose('Call %s for %s' % (self.stop_plugin, self.repository))
        if not self.stop_plugin(self.components, clients, self.cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        
        if self.new_clients:
            self.stdio.verbose('use new clients')
            for server in self.cluster_config.servers:
                new_client = self.new_clients[server]
                server_config = self.cluster_config.get_server_conf(server)
                chown_cmd = 'sudo chown -R %s:' % new_client.config.username
                for key in ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']:
                    if key in server_config:
                        chown_cmd += ' %s' % server_config[key]
                if not new_client.execute_command(chown_cmd):
                    self.stdio.stop_loading('stop_loading', 'fail')
                    return False
                self.dir_read_check(new_client, server_config['home_path'])
                self.now_clients[server] = new_client
            clients = self.new_clients

        cluster_config = self.new_cluster_config if self.new_cluster_config else self.cluster_config
        self.stdio.verbose('Call %s for %s' % (self.start_plugin, self.repository))
        if not self.start_plugin(self.components, clients, cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io, local_home_path=self.local_home_path, repository_dir=self.repository.repository_dir):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
        return True

    def rolling(self, zones_servers):
        self.stdio.start_loading('Observer rotation restart')
        all_servers = self.cluster_config.servers
        pre_zone = None
        for zone in zones_servers:
            self.cluster_config.servers = zones_servers[zone]
            if self.new_cluster_config:
                self.new_cluster_config.servers = zones_servers[zone]
            if not self.start_zone(pre_zone):
                self.stdio.stop_loading('stop_loading', 'fail')
                return False
            while True:
                for server in zones_servers[zone]:
                    config = self.cluster_config.get_server_conf(server)
                    sql = '''
                    select count(*) as cnt from oceanbase.__all_tenant as a left join (
                        select tenant_id, refreshed_schema_version 
                        from oceanbase.__all_virtual_server_schema_info 
                        where svr_ip = %s and svr_port = %s and refreshed_schema_version > 1
                        ) as b on a.tenant_id = b.tenant_id 
                    where b.tenant_id is null'''
                    if self.execute_sql(sql, args=(server.ip, config['rpc_port'])).get('cnt'):
                        break
                else:
                    break
                time.sleep(3)

            while self.execute_sql("select * from oceanbase.__all_virtual_clog_stat where table_id = 1099511627777 and status != 'ACTIVE'"):
                time.sleep(3)
            
            self.stop_zone(zone)
            if not self._restart():
                return False
            pre_zone = zone
            
        if not self.start_zone(pre_zone):
            self.stdio.stop_loading('stop_loading', 'fail')
            return False
            
        self.cluster_config.servers = all_servers
        if self.new_cluster_config:
            self.new_cluster_config.servers = all_servers
        self.stdio.stop_loading('succeed')
        return True

    def un_rolling(self):
        self.stdio.start_loading('Observer restart')

        if not self._restart():
            return False

        self.wait()
        self.stdio.stop_loading('succeed')
        return True

    def restart(self):
        zones_servers = {}
        all_servers = self.cluster_config.servers
        if self.connect():
            self.stdio.start_loading('Server check')
            servers = self.execute_sql("select * from oceanbase.__all_server", one=False, error=False)
            if len(self.cluster_config.servers) == len(servers):
                for server in servers:
                    if server['status'] != 'active' or server['stop_time'] > 0 or server['start_service_time'] == 0:
                        break
                else:
                    for server in self.cluster_config.servers:
                        config = self.cluster_config.get_server_conf_with_default(server)
                        zone = config['zone']
                        if zone not in zones_servers:
                            zones_servers[zone] = []
                        zones_servers[zone].append(server)
                    servers = self.cluster_config.servers
            self.stdio.stop_loading('succeed')
        ret = False
        try:
            if len(zones_servers) > 2:
                ret = self.rolling(zones_servers)
            else:
                ret = self.un_rolling()
        
            if ret and self.connect():
                self.display_plugin(self.components, self.new_clients if self.new_clients else self.clients, self.new_cluster_config if self.new_cluster_config else self.cluster_config, self.plugin_context.cmd, self.plugin_context.options, self.sub_io, cursor=self.cursor)
                if self.new_cluster_config:
                    self.stdio.verbose('Call %s for %s' % (self.reload_plugin, self.repository))
                    self.reload_plugin(self.components, self.clients, self.cluster_config, [], {}, self.sub_io, 
                    cursor=self.cursor, new_cluster_config=self.new_cluster_config, repository_dir=self.repository.repository_dir)
        except Exception as e:
            self.stdio.exception('Run Exception: %s' % e)
        finally:
            self.cluster_config.servers = all_servers
            if self.new_cluster_config:
                self.new_cluster_config.servers = all_servers
        if not ret:
            self.rollback()
        return ret


def restart(plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config=None, new_clients=None, rollback=False, *args, **kwargs):
    task = Restart(plugin_context, local_home_path, start_plugin, reload_plugin, stop_plugin, connect_plugin, display_plugin, repository, new_cluster_config, new_clients)
    call = task.rollback if rollback else task.restart
    if call():
        plugin_context.return_true()
