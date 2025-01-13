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


def get_binlog_instances(plugin_context, tenant_name=None, source_option=None, show_result=True, *args, **kwargs):
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('binlog_cursor')
    if not cursor:
        stdio.warn('Failed to get binlog cursor')
        return plugin_context.return_true()

    cluster_name = plugin_context.get_variable('cluster_name', None)
    sql = 'SHOW BINLOG INSTANCES'
    if cluster_name and tenant_name:
        sql += f" FOR `{cluster_name}`.`{tenant_name}`"

    show_result and stdio.start_loading('Waiting for binlog instance check')
    ret = {}
    count = 30
    while count:
        count -= 1
        ret = cursor.fetchall(sql)
        instance_num = len(ret)
        if not source_option or not show_result:
            break
        elif source_option == 'start':
            for instance in ret:
                if instance['convert_running'] == 'Yes':
                    instance_num -= 1
        elif source_option == 'stop':
            for instance in ret:
                if instance['convert_running'] == 'No':
                    instance_num -= 1
        if instance_num == 0:
            break
        else:
            time.sleep(2)

    if count == 0:
        stdio.error('Timeout waiting for binlog instance check.')
        show_result and stdio.stop_loading('fail')
        return plugin_context.return_false()

    if show_result:
        if len(ret) > 0:
            stdio.print_list(ret, ['name', 'ob_cluster', 'ob_tenant', 'ip', 'port', 'status', 'convert_running'],
                             lambda x: [x['name'], x['ob_cluster'], x['ob_tenant'], x['ip'], x['port'], x['state'], x['convert_running']],
                             title='Binlog Instances List')
        elif source_option != 'drop':
            stdio.print('No binlog instance found')

    if source_option and show_result:
        stdio.print('update binlog instance status successfully')

    show_result and stdio.stop_loading('succeed')
    return plugin_context.return_true(binlog_instances=ret)

