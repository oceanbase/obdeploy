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
import os


def chown_dir(plugin_context, new_clients, *args, **kwargs):
    if not new_clients:
        return plugin_context.return_true()
    def dir_read_check(client, path):
        if not client.execute_command('cd %s' % path):
            dirpath, _ = os.path.split(path)
            return dir_read_check(client, dirpath) and client.execute_command('sudo chmod +1 %s' % path)
        return True

    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    dir_list = plugin_context.get_variable('dir_list')
    stdio.verbose('use new clients')
    for server in cluster_config.servers:
        new_client = new_clients[server]
        server_config = cluster_config.get_server_conf(server)
        chown_cmd = 'sudo chown -R %s:' % new_client.config.username
        for key in dir_list:
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
            stdio.stop_loading('stop_loading', 'fail')
            return False
        dir_read_check(new_client, server_config['home_path'])

    return plugin_context.return_true()
