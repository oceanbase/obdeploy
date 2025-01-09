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


stdio = None
success = True


def start_check_pre(plugin_context, init_check_status=False, strict_check=False, work_dir_check=False, *args, **kwargs):
    global stdio
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    check_status = {}
    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()

        for comp in ["oceanbase", "oceanbase-ce"]:
            if comp in cluster_config.depends:
                check_status[server]['password'] = err.CheckStatus()
        check_status[server]['proxy_id'] = err.CheckStatus()
    plugin_context.set_variable('start_check_status', check_status)
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    def check_pass(server ,item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS
    def check_fail(server, item, error, suggests=[]):
        status = check_status[server][item]
        if status.status == err.CheckStatus.WAIT:
            status.error = error
            status.suggests = suggests
            status.status = err.CheckStatus.FAIL
    def wait_2_pass(server):
        status = check_status[server]
        for item in status:
            check_pass(server, item)
    def alert(server, item, error, suggests=[]):
        global success
        if strict_check:
            success = False
            check_fail(server, item, error, suggests)
            stdio.error(error)
        else:
            stdio.warn(error)
    def critical(server, item, error, suggests=[]):
        global success
        success = False
        check_fail(server, item, error, suggests)
        stdio.error(error)
    def get_success():
        global success
        return success

    def change_success():
        global success
        success = True

    plugin_context.set_variable('check_pass', check_pass)
    plugin_context.set_variable('check_fail', check_fail)
    plugin_context.set_variable('wait_2_pass', wait_2_pass)
    plugin_context.set_variable('alert', alert)
    plugin_context.set_variable('critical', critical)
    change_success()
    plugin_context.set_variable('get_success', get_success)

    return plugin_context.return_true()