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
from const import SERVICE_MODE

def switchover_log_resource(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    options = plugin_context.options
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    standby_tenant = cmds[1]
    standby_deploy = cmds[0]
    log_resource_type = getattr(options, 'type')

    stdio.start_loading("switching log resource")

    if log_resource_type == SERVICE_MODE:
        primary_deploy = plugin_context.get_variable('primary_deploy')
        primary_tenant = plugin_context.get_variable('primary_tenant')
        standbyro_password = plugin_context.get_variable('standbyro_password')

        primary_cursor = cursors.get(primary_deploy)
        sql = '''select group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host  from oceanbase.cdb_ob_access_point where tenant_name=%s)'''
        res = primary_cursor.fetchone(sql, (primary_tenant, ))
        if not res:
            stdio.error(f'{primary_deploy}:{primary_tenant} ip_list query error.')
            return
        ip_list = res['ip_list']

        sql = "SELECT LOG_MODE FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME='%s'" % primary_tenant
        res = primary_cursor.fetchone(sql)
        if not res or res['LOG_MODE'] is None:
            stdio.error(f'{primary_deploy}:{primary_tenant} LOG_MODE query error.')
            return
        if res['LOG_MODE'] == 'NOARCHIVELOG':
            sql = "ALTER SYSTEM ARCHIVELOG TENANT = %s" % primary_tenant
            res = primary_cursor.execute(sql, raise_exception=True, stdio=stdio)
            if not res:
                return

        standby_cursor = cursors.get(standby_deploy)
        sql = f"ALTER SYSTEM SET LOG_RESTORE_SOURCE = 'SERVICE={ip_list} USER=standbyro@{primary_tenant} PASSWORD={standbyro_password}' TENANT = {standby_tenant}"
        res = standby_cursor.execute(sql, raise_exception=True, stdio=stdio)
        if not res:
            return
    else:
        archive_log_uri = plugin_context.get_variable('archive_log_uri')
        cursor = cursors.get(cmds[0])
        if not cursor:
            stdio.error(f"get {standby_deploy} cursor is failed")
            return

        sql = f"ALTER SYSTEM SET LOG_RESTORE_SOURCE ='location={archive_log_uri}' TENANT = {standby_tenant}"
        res = cursor.execute(sql, raise_exception=False, stdio=stdio)
        if not res:
            stdio.error("Failed to set the log recovery source")
            return

    stdio.stop_loading("succeed")
    return plugin_context.return_true()
