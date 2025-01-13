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

import const


def instance_manager(plugin_context, source_option, no_instance_exit=True, *args, **kwargs):
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('binlog_cursor')
    if source_option not in const.BINLOG_INSTANCE_OPERATORS:
        stdio.error('Invalid manager binlog source_option: %s' % source_option)
        return plugin_context.return_false()

    instances = plugin_context.get_return('get_binlog_instances').get_return('binlog_instances')
    if not instances:
        if no_instance_exit:
            stdio.error('No binlog instance found, update instance failed.')
            return plugin_context.return_false()
        else:
            return plugin_context.return_true()
    try:
        if source_option == 'drop':
            for instance in instances:
                cursor.execute('DROP BINLOG INSTANCE %s FORCE;' % instance['name'], raise_exception=True)
        else:
            for instance in instances:
                if instance['state'] != const.BINLOG_INSTANCE_STATUS_OPERATORS_MAP[source_option]:
                    success = False
                    count = 30
                    time.sleep(3)
                    while count > 0 and not success:
                        ret = cursor.fetchall('SHOW BINLOG INSTANCES', raise_exception=True)
                        for new_instance in ret:
                            if new_instance['name'] == instance['name']:
                                if new_instance['state'] == const.BINLOG_INSTANCE_STATUS_OPERATORS_MAP[source_option]:
                                    success = True
                                    break
                        cursor.execute('%s BINLOG INSTANCE %s;' % (str(source_option).upper(), instance['name']), exc_level='warn', raise_exception=False)
                        stdio.verbose('Waiting for binlog instance %s to be %s' % (instance['name'], const.BINLOG_INSTANCE_STATUS_OPERATORS_MAP[source_option]))
                        time.sleep(5)
                        ret = cursor.fetchall('SHOW BINLOG INSTANCES', raise_exception=True)
                        for new_instance in ret:
                            if new_instance['name'] == instance['name']:
                                if new_instance['state'] == const.BINLOG_INSTANCE_STATUS_OPERATORS_MAP[source_option]:
                                    success = True
                                    break
                        count -= 1
    except:
        stdio.exception('Failed to update binlog instance status')
        return plugin_context.return_false()

    plugin_context.set_variable('instances_operator', source_option)
    return plugin_context.return_true()

