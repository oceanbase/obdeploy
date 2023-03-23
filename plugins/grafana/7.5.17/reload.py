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

from tool import YamlLoader

import re

yaml = YamlLoader()


def reload(plugin_context, cursor, new_cluster_config,  *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    servers = cluster_config.servers

    stdio.start_loading('Reload Grafana')
    global_ret = True
    for server in servers:
        stdio.verbose('%s reload grafana ' % server)
        new_server_config = new_cluster_config.get_server_conf(server)
        api_cursor = cursor.get(server)
        grafana_new_pwd = new_server_config['login_password']
        if grafana_new_pwd == 'admin':
            stdio.error("%s grafana admin password should not be 'admin'" % server)
            global_ret = False
            continue
        if len(grafana_new_pwd) < 5:
            stdio.error("%s grafana admin password length should not be less than 5" % server)
            global_ret = False
            continue
        ret = api_cursor.modify_password(grafana_new_pwd, stdio=stdio)
        if ret:
            cluster_config.update_server_conf(server, 'login_password', grafana_new_pwd, False)
        else:  
            global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
