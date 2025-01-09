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

import _errno as err


stdio = None
success = True


def start_check_pre(plugin_context, init_check_status=False, work_dir_check=False, *args, **kwargs):
    def check_pass(server, item):
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
            check_pass(server ,item)

    def critical(server, item, error, suggests=[]):
        global success
        success = False
        check_fail(server, item, error, suggests)
        stdio.error(error)

    def get_success():
        global success
        return success

    plugin_context.set_variable('check_pass', check_pass)
    plugin_context.set_variable('check_fail', check_fail)
    plugin_context.set_variable('wait_2_pass', wait_2_pass)
    plugin_context.set_variable('critical', critical)
    plugin_context.set_variable('get_success', get_success)

    cluster_config = plugin_context.cluster_config
    global stdio
    stdio = plugin_context.stdio
    check_status = {}
    plugin_context.set_variable('start_check_status', check_status)
    depends = ['obagent']
    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    username = None
    password = None

    for comp in cluster_config.depends:
        if comp in depends:
            for server in cluster_config.get_depend_servers(comp):
                obagent_config = cluster_config.get_depend_config(comp, server)
                check_ret = True
                if username is not None and username != obagent_config.get('http_basic_auth_user', ''):
                    check_ret = False
                if password is not None and password != obagent_config.get('http_basic_auth_password', ''):
                    check_ret = False
                if not check_ret:
                    stdio.warn('The http basic auth of obagent is inconsistent, and some targets in the scrape_configs may not work.')
                    break
                password = obagent_config.get('http_basic_auth_password', '')
                username = obagent_config.get('http_basic_auth_user', '')
    return plugin_context.return_true()