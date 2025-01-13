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