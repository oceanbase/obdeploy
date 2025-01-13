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

from _errno import EC_OBSERVER_INVALID_MODFILY_GLOBAL_KEY

def obshell_password_reload(plugin_context, *args, **kwargs):
    global_ret = True
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    global_change_conf = plugin_context.get_variable('global_change_conf')
    change_conf = plugin_context.get_variable('change_conf')
    server = cluster_config.servers[0]
    for key in global_change_conf:
        try:
            value = change_conf[server][key] if change_conf[server].get(key) is not None else ''
            if key == 'root_password':
                for server in servers:
                    stdio.verbose('update %s obshell password' % (server))
                    server_config = cluster_config.get_server_conf(server)
                    obshell_port = server_config.get('obshell_port')
                    client = ClientSet(server.ip, obshell_port, PasswordAuth(value))
                    client.v1.get_ob_info()
        except:
            stdio.exception("")
            global_ret = False
    
    if not global_ret:
        return plugin_context.return_false()
    return plugin_context.return_true()