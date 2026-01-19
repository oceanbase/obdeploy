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

def switchover_location_tenant(plugin_context, cluster_configs, cursors={}, primary_info={}, *args, **kwargs):
    def error(msg='', *arg, **kwargs):
        stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('failed')

    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    standby_cluster = cmds[0]
    standby_tenant = cmds[1]
    standby_cursor = cursors.get(standby_cluster)

    primary_cluster = plugin_context.get_variable('primary_deploy')
    primary_tenant = plugin_context.get_variable('primary_tenant')
    primary_cursor = cursors.get(primary_cluster)

    if not primary_cursor:
        stdio.error('Failed to connect primary deploy: {}.'.format(primary_cluster))
        return False
    if not standby_cursor:
        stdio.error('Failed to connect standby deploy: {}.'.format(standby_cluster))
        return False
    sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME='%s'" % primary_tenant
    primary_res = primary_cursor.fetchone(sql)
    if not primary_res:
        error("Primary tenant {}:{} not exists".format(primary_cluster, primary_tenant))
        return
    if primary_res['TENANT_ROLE'] != 'PRIMARY':
        error("Srimary tenant {}:{}'s role is invalid,current not support non-primary tenant as primary to switchover. ".format(primary_cluster, primary_tenant))
        return
    
    # Check whether the standby tenant has enabled archive mode
    sql = 'select TENANT_ID,LOG_MODE,SYNC_SCN from oceanbase.DBA_OB_TENANTS where tenant_name = %s'
    standby_info_res = standby_cursor.fetchone(sql, (standby_tenant, ))
    if not standby_info_res:
        error('select standby tenant failed')
        return
    if standby_info_res['LOG_MODE'] == 'NOARCHIVELOG':
        error(f'Log-archiving-based {standby_tenant} tenant requires archiving to be completed prior to switchover.')
        return
    standby_tenant_id = standby_info_res['TENANT_ID']

    startTime = round(time.time() * 1000)    
    max_delay_time = 120000
    sql = "SELECT TENANT_ID, TENANT_NAME, TENANT_TYPE, PRIMARY_ZONE, LOCALITY, COMPATIBILITY_MODE, STATUS, IN_RECYCLEBIN, (CASE WHEN LOCKED = 'YES' THEN 1 ELSE 0 END) AS LOCKED, TIMESTAMPDIFF(SECOND, CREATE_TIME, now()) AS exist_seconds " \
              ", ARBITRATION_SERVICE_STATUS, SWITCHOVER_STATUS, LOG_MODE, SYNC_SCN, RECOVERY_UNTIL_SCN, TENANT_ROLE FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_TYPE IN ('SYS', 'USER') and tenant_id = %s"
    primary_tenant_info = primary_cursor.fetchone(sql, (primary_res['TENANT_ID'], ), raise_exception=True)
    if not primary_tenant_info:
        error("Query primary tenant {}'s info for calculate standby tenant {} sync delay time failed".format(primary_tenant, standby_tenant))
        return
    query_time = round(time.time() * 1000) - startTime
    delay_time = (primary_tenant_info['SYNC_SCN'] - standby_info_res['SYNC_SCN']) / 1000000 - query_time
    stdio.verbose("primary {} syncScn={}, standby {} syncScn={}, sql query time is {}ms, sync delay time is {}ms".format(primary_tenant, primary_tenant_info.get('SYNC_SCN'), standby_tenant, standby_info_res['SYNC_SCN'], query_time, delay_time))
    delay_time = 0 if delay_time < 0 else delay_time
    if delay_time > max_delay_time:
        error("Standby tenant {}:{} synchronization delay:{}ms is greater than the threshold:{}ms, place retry when delay < {} ".format(standby_cluster, standby_tenant, delay_time, max_delay_time, max_delay_time))
        return
    
    stdio.start_loading("switchover tenant")

    # Confirm whether the archive status of the standby tenant is DOING
    sql = "SELECT STATUS FROM oceanbase.CDB_OB_ARCHIVELOG WHERE TENANT_ID=%s" % standby_tenant_id
    res = standby_cursor.fetchone(sql)
    if not res:
        error(f"Archive status query for the {standby_tenant} tenant failed.")
        return
    if res["STATUS"] != 'DOING':
        error("Archiving is not in a normal working state.")
        return

#     Verify whether the SWITCHOVER command can be executed successfully
    sql = "ALTER SYSTEM SWITCHOVER TO STANDBY TENANT = %s VERIFY" % primary_tenant
    res = primary_cursor.execute(sql, raise_exception=True, stdio=stdio)
    if not res:
        error()
        return

#     Switch the primary tenant to the standby tenant
    sql = "ALTER SYSTEM SWITCHOVER TO STANDBY TENANT = %s" % primary_tenant
    if primary_cursor.execute(sql,raise_exception=True, stdio=stdio) is False:
        error()
        return
    
    # Confirm whether the primary tenant has been switched to the standby tenant
    sql = "SELECT TENANT_ROLE,SWITCHOVER_STATUS FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME='%s'" % primary_tenant
    res = primary_cursor.fetchone(sql)
    if not res:
        error(f"Failed to query the {primary_tenant} primary to standby switchover information.")
        return
    if res['TENANT_ROLE'] != 'STANDBY' or res['SWITCHOVER_STATUS'] != 'NORMAL':
        error(f"{primary_tenant} primary to standby switchover failed.")
        return
    
#     Check whether the log archiving on the original primary tenant is complete
    sql = 'select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME=%s'
    res = primary_cursor.fetchone(sql, (primary_tenant,))
    if not res and res['TENANT_ID'] is None:
        error('select primary tenant failed')
        return
    primary_tenant_id = res['TENANT_ID']

    options = plugin_context.options
    primary_archive_log_uri = getattr(options, 'primary_archive_log_uri', None)
    if not primary_archive_log_uri:
        sql = "SELECT VALUE FROM oceanbase.CDB_OB_ARCHIVE_DEST WHERE TENANT_ID=%s AND NAME='path'"
        res = primary_cursor.fetchone(sql, (primary_tenant_id, ))
        if not res:
            error("Primary tenant archiving path query failed")
            return
        get_backup_and_archive_uri = plugin_context.get_variable('get_backup_and_archive_uri')
        plugin_context.set_variable('primary_archive_log_uri', get_backup_and_archive_uri(res['VALUE']))
    else:
        plugin_context.set_variable('primary_archive_log_uri', primary_archive_log_uri)

    max_attempts = 1200
    interval_seconds = 5
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        sql = "SELECT SYNCHRONIZED FROM oceanbase.V$OB_ARCHIVE_DEST_STATUS WHERE TENANT_ID = %s"
        res = primary_cursor.fetchone(sql, (primary_tenant_id, ))
        if res and res['SYNCHRONIZED'] == 'YES':
            break
        else:
            if attempt >= max_attempts:
                error('Log archiving is not synchronized with tenant logs. Please restore the master-slave relationship.')
                return
            time.sleep(interval_seconds)

#     The sys tenant of the cluster where the standby tenant is located switches the standby tenant to the primary tenant
    sql = "ALTER SYSTEM SWITCHOVER TO PRIMARY TENANT = %s" % standby_tenant
    if standby_cursor.execute(sql, raise_exception=True, stdio=stdio) is False:
        error()
        return
    
    # Confirm whether the standby tenant has been switched to the primary tenant
    sql = "SELECT TENANT_ROLE,SWITCHOVER_STATUS FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME='%s'" % standby_tenant
    res = standby_cursor.fetchone(sql)
    if not res:
        error(f"Failed to query the {standby_tenant} standby to primary switchover information.")
        return
    if res['TENANT_ROLE'] != 'PRIMARY' or res['SWITCHOVER_STATUS'] != 'NORMAL':
        error(f"{standby_tenant} standby to primary switchover failed.")
        return

    archive_path = plugin_context.get_variable('standby_archive_log_uri')
    sql = "ALTER SYSTEM SET LOG_RESTORE_SOURCE ='LOCATION=%s' TENANT = %s" % (archive_path, primary_tenant)
    if primary_cursor.execute(sql,raise_exception=True, stdio=stdio) is False:
        error(f"Failed to configure the recovery source for the {primary_tenant}.")
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true()