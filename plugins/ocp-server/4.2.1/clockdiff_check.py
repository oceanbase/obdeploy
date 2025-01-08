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