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

import const


def stop_instance(plugin_context, binlog_cursor=None, *args, **kwargs):
    if plugin_context.get_variable('status_check_pass') is False:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    binlog_cursor = plugin_context.get_return('connect', spacename=const.COMP_OBBINLOG_CE).get_return('binlog_cursor') if not binlog_cursor else binlog_cursor

    sql = 'SHOW BINLOG INSTANCES'
    stdio.start_loading('Stop binlog instance')
    binlog_instances = binlog_cursor.fetchall(sql)
    success = True
    for binlog_instance in binlog_instances:
        name = binlog_instance['name']
        ips = binlog_instance['ip']
        state = binlog_instance['state']
        if state != 'Running':
            continue
        for ip in ips.split(','):
            server = next((server for server in cluster_config.servers if server.ip == ip), None)
            if not server:
                stdio.warn('%s(%s) binlog instance not in binlog server cluster' % (name, ip))
            cmd = "ps -aux | grep %s | grep binlog_instance | grep -v grep | awk '{print $2}' | xargs kill -9" % name
            client = clients[server]
            if not client.execute_command(cmd):
                stdio.warn('%s(%s) binlog instance stop failed' % (name, ip))
    if not success:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
