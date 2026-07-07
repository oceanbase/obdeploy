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
from tool import set_plugin_context_variables

success = True


def start_check_pre(
    plugin_context,
    init_check_status=False,
    work_dir_check=True,
    work_dir_empty_check=True,
    port_check=True,
    *args,
    **kwargs,
):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    check_status = {}

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
            check_pass(server, item)

    def critical(server, item, error, suggests=[]):
        global success
        success = False
        check_fail(server, item, error, suggests)
        stdio.error('{}, {}'.format(error, suggests[0].msg if suggests else ''))

    def alert(server, item, error, suggests=[]):
        stdio.warn(error)

    def get_success():
        global success
        return success

    def change_success():
        global success
        success = True

    servers_port = {}
    servers_clients = {}
    for server in cluster_config.servers:
        ip = server.ip
        servers_clients[ip] = clients[server]
        if ip not in servers_port:
            servers_port[ip] = {}
        check_status[server] = {
            'servers': err.CheckStatus(),
            'bootstrap_server': err.CheckStatus(),
            'port': err.CheckStatus(),
            'http_port': err.CheckStatus(),
            'memory_limit': err.CheckStatus(),
            'log_disk_size': err.CheckStatus(),
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()

    plugin_context.set_variable('start_check_status', check_status)
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    change_success()
    set_plugin_context_variables(plugin_context, {
        'start_check_status': check_status,
        'check_pass': check_pass,
        'check_fail': check_fail,
        'wait_2_pass': wait_2_pass,
        'critical': critical,
        'alert': alert,
        'get_success': get_success,
        'work_dir_check': work_dir_check,
        'work_dir_empty_check': work_dir_empty_check,
        'port_check': port_check,
        'servers_port': servers_port,
        'servers_clients': servers_clients,
    })
    return plugin_context.return_true()
