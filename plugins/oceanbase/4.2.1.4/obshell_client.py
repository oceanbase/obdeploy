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

from obshell import ClientSet
from obshell.auth import PasswordAuth


def obshell_client(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    obshell_clients = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        root_password = server_config.get('root_password', '')
        obshell_port = server_config.get('obshell_port')
        client = ClientSet(server.ip, obshell_port, PasswordAuth(root_password))
        obshell_clients[server.ip] = client

    plugin_context.set_variable('obshell_clients', obshell_clients)
    return plugin_context.return_true()
