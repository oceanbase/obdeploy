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