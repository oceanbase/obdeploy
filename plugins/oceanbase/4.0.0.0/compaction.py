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


def compaction(plugin_context, cursor=None, *args, **kwargs):
 
    stdio = plugin_context.stdio
    
    # Get cursor if not provided
    if not cursor:
        connect_ret = plugin_context.get_return('connect')
        if not connect_ret:
            stdio.warn('Failed to get connection, skip compaction')
            return plugin_context.return_true()
        cursor = connect_ret.get_return('cursor')
        if not cursor:
            stdio.warn('Failed to get cursor, skip compaction')
            return plugin_context.return_true()

    stdio.start_loading('Minor freeze')
    sql_statements = [
        "ALTER SYSTEM MINOR FREEZE TENANT = sys;",
        "ALTER SYSTEM MINOR FREEZE TENANT = all_user;",
        "ALTER SYSTEM MINOR FREEZE TENANT = all_meta;"
    ]

    for sql in sql_statements:
        tenant_name = sql.split('=')[1].strip().rstrip(';')
        if cursor.execute(sql, raise_exception=False, exc_level='verbose') is False:
            stdio.warn('Failed to execute minor freeze for tenant: %s' % tenant_name)
        else:
            stdio.verbose('Minor freeze executed successfully for tenant: %s ' % tenant_name)
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()

