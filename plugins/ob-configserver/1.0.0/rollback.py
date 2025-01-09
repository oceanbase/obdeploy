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


def rollback(plugin_context, now_clients, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients

    dir_list = plugin_context.get_variable("dir_list")
    stdio.start_loading('Rollback')
    for server in cluster_config.servers:
        client = clients[server]
        new_client = now_clients[server]
        server_config = cluster_config.get_server_conf(server)
        chown_cmd = 'sudo chown -R %s:' % client.config.username
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
        new_client.execute_command(chown_cmd)
    stdio.stop_loading('succeed')