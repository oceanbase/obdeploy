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

from tool import get_option
import _errno as err

def get_source_type(plugin_context, cursor, *args, **kwargs):
    def error(msg='', *arg, **kwargs):
        stdio.stop_loading('failed')
        stdio.error(msg)

    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)
        

    stdio = plugin_context.stdio
    cmds = plugin_context.cmds

    cluster_name = cmds[0]
    tenant_name = cmds[1]
    stdio.start_loading("get log source type")
    sql = 'select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME=%s'
    res = cursor.fetchone(sql, (tenant_name, ))
    if not res or res['TENANT_ID'] is None:
        error(f"tenant {cluster_name}:{tenant_name} is not exist.")
        return
    tenant_id = res['TENANT_ID']

    sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s'
    res = cursor.fetchone(sql, (tenant_id, ))
    if not res or res['TYPE'] is None:
        error(f"{cluster_name}:{tenant_name} log restore source is not exist.")
        return

    stdio.stop_loading("succeed")
    return return_true(source_type=res['TYPE'])
