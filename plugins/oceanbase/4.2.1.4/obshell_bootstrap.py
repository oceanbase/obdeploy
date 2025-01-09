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

import requests.exceptions
from obshell import ClientSet
from obshell.auth import PasswordAuth
from obshell.model.info import Agentidentity


def obshell_bootstrap(plugin_context, need_bootstrap=None, *args, **kwargs):
    scale_out = plugin_context.get_variable('scale_out')
    if not need_bootstrap and not scale_out:
        return plugin_context.return_true()
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    stdio.start_loading('obshell bootstrap')
    time.sleep(3)
    try:
        count = 200
        obshell_clients = {}
        while count:
            take_over_count = 0
            for server in cluster_config.servers:
                if server not in obshell_clients:
                    server_config = cluster_config.get_server_conf(server)
                    root_password = server_config.get('root_password', '')
                    obshell_port = server_config.get('obshell_port')
                    client = ClientSet(server.ip, obshell_port,
                                       PasswordAuth(root_password))
                    obshell_clients[server] = client
                client = obshell_clients[server]
                try:
                    info = client.v1.get_info()
                except requests.exceptions.ConnectionError:
                    continue
                if info.identity == Agentidentity.TAKE_OVER_MASTER.value:
                    dag = client.v1.get_agent_last_maintenance_dag()
                    client.v1.wait_dag_succeed(dag.generic_id)
                    take_over_count = len(cluster_config.servers)
                    break
                elif info.identity == Agentidentity.CLUSTER_AGENT.value:
                    take_over_count += 1
            if take_over_count == len(cluster_config.servers):
                break
            time.sleep(3)
            count -= 1
        if count == 0:
            stdio.stop_loading('fail')
            stdio.error('obshell bootstrap failed: get obshell take over result timeout!')
            return plugin_context.return_false()
    except Exception as e:
        stdio.exception('')
        stdio.stop_loading('fail')
        stdio.error('obshell bootstrap failed: %s' % e)
        return plugin_context.return_false()

    stdio.stop_loading('succeed')

    return plugin_context.return_true()