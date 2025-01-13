# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import time

from tool import Cursor, set_plugin_context_variables


class RestartManager(object):

    def __init__(self, plugin_context):
        self.plugin_context = plugin_context
        self.cluster_config = plugin_context.cluster_config
        self.stdio = plugin_context.stdio
        self.db = None
        self.cursor = None

    def close(self):
        if self.db:
            self.cursor.close()
            self.cursor = None
            self.db = None

    def connect(self):
        if self.cursor is None or self.execute_sql('select version()', error=False) is False:
            count = 101
            while count:
                count -= 1
                for server in self.cluster_config.servers:
                    try:
                        server_config = self.cluster_config.get_server_conf(server)
                        password = server_config.get('root_password', '') if count % 2 == 0 else ''
                        cursor = Cursor(ip=server.ip, port=server_config['mysql_port'], tenant='', password=password if password is not None else '', stdio=self.stdio)
                        if cursor.execute('select 1', raise_exception=False, exc_level='verbose'):
                            if self.cursor:
                                self.close()
                            self.db = cursor.db
                            self.cursor = cursor
                            count = 0
                            break
                    except:
                        if count == 0:
                            return False
                time.sleep(3)
            while self.execute_sql('use oceanbase', error=False) is False:
                time.sleep(2)
            self.execute_sql('set session ob_query_timeout=1000000000')
        return True

    def execute_sql(self, query, args=None, one=True, error=True):
        exc_level = 'error' if error is True else 'verbose'
        if one:
            result = self.cursor.fetchone(query, args, exc_level=exc_level)
        else:
            result = self.cursor.fetchall(query, args, exc_level=exc_level)
        result and self.stdio.verbose(result)
        return result

    def broken_sql(self, sql, sleep_time=3):
        while True:
            ret = self.execute_sql(sql, error=False)
            if ret is None:
                break
            time.sleep(sleep_time)


def restart_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    restart_manager = RestartManager(plugin_context)

    if restart_manager.connect():
        zones_servers = {}
        stdio.start_loading('Server check')
        servers = restart_manager.execute_sql("select * from oceanbase.__all_server", one=False, error=False)
        if isinstance(servers, list) and len(cluster_config.servers) == len(servers):
            for server in servers:
                if server['status'] != 'active' or server['stop_time'] > 0 or server['start_service_time'] == 0:
                    break
            else:
                for server in cluster_config.servers:
                    config = cluster_config.get_server_conf_with_default(server)
                    zone = config['zone']
                    if zone not in zones_servers:
                        zones_servers[zone] = []
                    zones_servers[zone].append(server)
        stdio.stop_loading('succeed')
    else:
        return plugin_context.return_false()

    new_clients = kwargs.get('new_clients')
    new_deploy_config = kwargs.get('new_deploy_config')
    variables_dict = {
        "clients": plugin_context.clients,
        "restart_manager": restart_manager,
        "zones_servers": zones_servers,
        "dir_list": ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir', '.meta', 'log_obshell'],
        "new_clients": new_clients,
        "new_deploy_config": new_deploy_config
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()



