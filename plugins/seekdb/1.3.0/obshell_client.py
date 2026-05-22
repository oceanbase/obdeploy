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

import re

from obshell import ClientSet, ClientV1
from obshell.auth import PasswordAuth
from obshell.request import ProtocolOptions


def obshell_client(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    obshell_clients = {}
    if plugin_context.get_variable('seekdb_is_standby', default=False):
        return plugin_context.return_true()
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        root_password = server_config.get('root_password', '')
        obshell_port = server_config.get('obshell_port', 2886)
        client = ClientSet(server.ip, obshell_port, PasswordAuth(root_password))
        try:
            client.v1.get_info()
        except Exception as e:
            match = re.search(r'status code: (\d+)', str(e))
            if match and match.group(1) == '400':
                client = ClientV1(
                    server.ip,
                    obshell_port,
                    PasswordAuth(root_password),
                    protocol_options=ProtocolOptions.https_insecure(),
                )
            else:
                stdio = plugin_context.stdio
                stdio.error(f'Failed to connect obshell {server.ip}:{obshell_port}')
                return plugin_context.return_false()
        obshell_clients[server.ip] = client

    plugin_context.set_variable('obshell_clients', obshell_clients)
    return plugin_context.return_true()

