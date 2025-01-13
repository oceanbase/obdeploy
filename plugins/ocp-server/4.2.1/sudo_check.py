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

import _errno as err


def sudo_check(plugin_context, **kwargs):
    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    stdio.verbose('sudo nopasswd check')
    for server in cluster_config.servers:
        client = clients[server]

        if not (client.execute_command('sudo -n true') or client.execute_command('[ `id -u` == "0" ]')):
            critical(server, 'sudo nopasswd', err.EC_OCP_SERVER_SUDO_NOPASSWD.format(ip=str(server), user=client.config.username),
                     [err.SUG_OCP_SERVER_SUDO_NOPASSWD.format(ip=str(server), user=client.config.username)])
            continue
        check_pass(server, 'sudo nopasswd')
    return plugin_context.return_true()