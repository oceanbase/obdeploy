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


def bootstrap(plugin_context, cursor = None, start_env=None, *args, **kwargs):
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    if not cursor:
        cursor = plugin_context.get_return('connect').get_return('cursor')

    if not start_env:
        raise Exception("start env is needed")
    success = True
    for server in start_env:
        server_config = start_env[server]
        data = {
            "cluster": {
                "name": server_config["cluster_name"],
                "obClusterId": server_config["ob_cluster_id"],
                "rootSysPassword": server_config["root_sys_password"],
                "serverAddresses": server_config["server_addresses"],
            },
            "agentUsername": server_config["agent_username"],
            "agentPassword": server_config["agent_password"]
        }
        if server not in cursor or not cursor[server].init(data, stdio=stdio):
            stdio.error("failed to send init request to {} ocp express".format(server))
            success = False
        else:
            client = clients[server]
            bootstrap_flag = os.path.join(server_config['home_path'], '.bootstrapped')
            client.execute_command('touch %s' % bootstrap_flag)

    if success:
        return plugin_context.return_true()
    else:
        return plugin_context.return_false()

