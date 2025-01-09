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
