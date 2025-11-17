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
from _types import Capacity


def web_upgrade_check(plugin_context, path, init_check_status=False, *args, **kwargs):
    def check_pass(item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS
    def check_fail(item, error, suggests=[]):
        status = check_status[server][item]
        status.error = error
        status.suggests = suggests
        status.status = err.CheckStatus.FAIL

    def error(item, _error, suggests=[]):
        global success
        success = False
        check_fail(item, _error, suggests)
        stdio.error(_error)


    check_status = {}
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    plugin_context.set_variable('start_check_status', check_status)


    for server in cluster_config.servers:
        check_status[server] = {
            'path': err.CheckStatus(),
        }

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before upgrade %s' % cluster_config.name)
    success = True

    for server in cluster_config.servers:
        client = clients[server]
        if Capacity(client.execute_command(f"df -BG {path} | awk 'NR==2 {{print $4}}'").stdout.strip()).bytes > 20 << 30:
            error('path', err.EC_OMS_NOT_ENOUGH_DISK.format(ip=server.ip, disk=path, need='20G'))
    check_pass('path')

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()



