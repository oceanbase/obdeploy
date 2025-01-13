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


def clockdiff_check(plugin_context, **kwargs):
    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    for server in cluster_config.servers:
        client = clients[server]
        try:
            # clockdiff status check
            stdio.verbose('clockdiff check ')
            clockdiff_cmd = 'clockdiff -o 127.0.0.1'
            if client.execute_command(clockdiff_cmd):
                check_pass(server, 'clockdiff')
            else:
                if not client.execute_command('sudo -n true'):
                    critical(server, 'clockdiff', err.EC_OCP_SERVER_CLOCKDIFF_NOT_EXISTS.format(server=server))
                ret = client.execute_command('sudo ' + clockdiff_cmd)
                if not ret:
                    critical(server, 'clockdiff', err.EC_OCP_SERVER_CLOCKDIFF_NOT_EXISTS.format(server=server))

                clockdiff_bin = 'type -P clockdiff'
                res = client.execute_command(clockdiff_bin).stdout
                client.execute_command('sudo chmod u+s %s' % res)
                client.execute_command("sudo setcap 'cap_sys_nice+ep cap_net_raw+ep' %s" % res)
        except Exception as e:
            stdio.error(e)
            critical(server, 'clockdiff', err.EC_OCP_SERVER_CLOCKDIFF_NOT_EXISTS.format(server=server))
            continue
        check_pass(server, 'clockdiff')
    return plugin_context.return_true()