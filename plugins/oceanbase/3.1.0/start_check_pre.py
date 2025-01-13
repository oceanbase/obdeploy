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


success = False
production_mode = False


def start_check_pre(plugin_context, init_check_status=False, strict_check=False, work_dir_check=False, *args, **kwargs):

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

    def alert_strict(server, item, error, suggests=[]):
        global success, production_mode
        if strict_check or production_mode:
            success = False
            check_fail(server, item, error, suggests)
            print_with_suggests(error, suggests)
        else:
            stdio.warn(error)

    def error(server, item, _error, suggests=[]):
        global success
        if plugin_context.dev_mode:
            stdio.warn(_error)
        else:
            check_fail(server, item, _error, suggests)
            print_with_suggests(_error, suggests)
            success = False

    def get_success():
        global success
        return success

    def change_success():
        global success
        success = True

    def print_with_suggests(error, suggests=[]):
        stdio.error('{}, {}'.format(error, suggests[0].msg if suggests else ''))

    kernel_check_items = [
        {'check_item': 'vm.max_map_count', 'need': [327600, 1310720], 'recommend': 655360},
        {'check_item': 'vm.min_free_kbytes', 'need': [32768, 2097152], 'recommend': 2097152},
        {'check_item': 'vm.overcommit_memory', 'need': 0, 'recommend': 0},
        {'check_item': 'fs.file-max', 'need': [6573688, float('inf')], 'recommend': 6573688},
    ]

    kernel_check_status = {}
    for kernel_param in kernel_check_items:
        check_item = kernel_param['check_item']
        kernel_check_status[check_item] = err.CheckStatus()

    check_status ={}
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global production_mode

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        production_mode = server_config.get('production_mode', False)
        check_status[server] = {
            'port': err.CheckStatus(),
            'mem': err.CheckStatus(),
            'disk': err.CheckStatus(),
            'ulimit': err.CheckStatus(),
            'aio': err.CheckStatus(),
            'net': err.CheckStatus(),
            'ntp': err.CheckStatus(),
        }
        check_status[server].update(kernel_check_status)
        if work_dir_check:
             check_status[server]['dir'] = err.CheckStatus()

    plugin_context.set_variable('start_check_status', check_status)
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    clog_sub_dir = 'ilog'

    max_user_processes = {
        'need': lambda x: 4096,
        'recd': lambda x: 4096 * x,
        'name': 'nproc'
    }

    variable_dict = {
        'start_check_status': check_status,
        'kernel_check_items': kernel_check_items,
        'max_user_processes': max_user_processes,
        'clog_sub_dir': clog_sub_dir,
        'check_pass': check_pass,
        'check_fail': check_fail,
        'wait_2_pass': wait_2_pass,
        'alert': alert,
        'alert_strict': alert_strict,
        'error': error,
        'critical': critical,
        'get_success': get_success,
        'print_with_suggests': print_with_suggests,
        'production_mode': production_mode
    }
    change_success()
    set_plugin_context_variables(plugin_context, variable_dict)

    return plugin_context.return_true()