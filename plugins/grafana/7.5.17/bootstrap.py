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

import re
import time
import os


def bootstrap(plugin_context, cursor=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    servers = cluster_config.servers
    if not cursor:
        cursor = plugin_context.get_return('connect').get_return('cursor')

    stdio.start_loading('grafana admin user password set')
    count = 10
    failed_message = []
    while servers and count:
        count -= 1
        failed_servers = []
        
        for server in servers:
            stdio.verbose('%s grafana admin user password set' % server)
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            touch_path = os.path.join(home_path, 'run/.grafana')
            if client.execute_command("ls %s" % touch_path):
                stdio.stop_loading('succeed')
                plugin_context.return_true()
                continue
            api_cursor = cursor.get(server)
            grafana_new_pwd = server_config['login_password']
            if api_cursor.modify_password(grafana_new_pwd, stdio=stdio):
                stdio.verbose("%s grafana admin password set ok" % server)
                client.execute_command("touch %s" % touch_path )
                continue            
            stdio.verbose('failed to set %s grafana admin user password, remaining retries: %d' % (server, count))
            if count:
                failed_servers.append(server)
            else:
                failed_message.append('failed to set %s grafana admin user password' % server)
        servers = failed_servers
        if servers and count:
            time.sleep(1)
    
    if failed_message:
        stdio.stop_loading('failed')
        for msg in failed_message:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true()

