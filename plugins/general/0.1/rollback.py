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
            if key in server_config:
                chown_cmd += ' %s' % server_config[key]
        new_client.execute_command(chown_cmd)
    stdio.stop_loading('succeed')