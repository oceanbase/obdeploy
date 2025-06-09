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

def standby_log_recover(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    cmds = plugin_context.cmds
    cluster_name = cmds[0]
    tenant_name = cmds[1]
    
    stdio.start_loading("Setting up continuous log synchronization.")

    sql = 'SELECT TENANT_ROLE, STATUS FROM oceanbase.DBA_OB_TENANTS where tenant_name=%s'
    res = cursor.fetchone(sql, (tenant_name, ))
    if not res:
        stdio.error('Query {}:{} tenant fail.'.format(cluster_name, tenant_name))
        return

    if res['TENANT_ROLE'] != "STANDBY":
        stdio.error(f"The standby tenant {tenant_name} has not been restored yet. Please try again later.")
        return
    if res['STATUS'] != 'NORMAL':
        stdio.error(f"{tenant_name} status is not normal, recover is not allowed. Please try again later.")
        return

    sql = f"ALTER SYSTEM RECOVER STANDBY TENANT = {tenant_name} UNTIL "
    timestamp = get_option(options, 'timestamp', None)
    scn = get_option(options, 'scn', None)
    if timestamp:
        sql += f"Time='{timestamp}'"
    elif scn:
        sql += f"SCN={scn}"
    else:
        sql += "UNLIMITED"

    res = cursor.execute(sql, raise_exception=True, stdio=stdio)
    if not res:
        stdio.error("Standby tenant log replay point configuration failed.")
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true()