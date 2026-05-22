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

from const import MAX_AVAILABILITY, MAX_PROTECTION
import time


def set_tenant_sync_mode(plugin_context, cursors=None, create_tenant_options=[], standbyro_password='', *args, **kwargs):
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds

    standby_deploy_name = plugin_context.cluster_config.deploy_name
    primary_deploy_name = cmds[1]
    primary_tenant = cmds[2]
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]

    primary_cursor = cursors.get(primary_deploy_name)
    standby_cursor = cursors.get(standby_deploy_name)
    if not primary_cursor or not standby_cursor:
        stdio.error('Missing cursor for primary or standby deploy.')
        return plugin_context.return_false()

    for options in multi_options:
        sync_mode = getattr(options, 'sync_mode', 'performance').strip()
        if sync_mode == 'performance':
            continue

        stdio.start_loading('Set tenant sync mode %s' % sync_mode)

        standby_tenant = getattr(options, 'tenant_name') or primary_tenant
        sql = 'select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)'
        primary_res = primary_cursor.fetchone(sql, (primary_tenant,))
        if not primary_res or not primary_res['ip_list']:
            stdio.error("fail to get {}'s ip list".format(primary_deploy_name))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        standby_res = standby_cursor.fetchone(sql, (standby_tenant,))
        if not standby_res or not standby_res['ip_list']:
            stdio.error("fail to get {}'s ip list".format(standby_deploy_name))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        # Escape password for use inside double-quoted SYNC_STANDBY_DEST string (same as set_sync_mode.py)
        pwd_escaped = (standbyro_password or '').replace('\\', '\\\\').replace('"', '\\"')

        if sync_mode == "protection":
            dest_primary = 'SERVICE=%s USER=%s PASSWORD=%s' % (standby_res['ip_list'], f'standbyro@{standby_tenant}', pwd_escaped)
            dest_standby = 'SERVICE=%s USER=%s PASSWORD=%s' % (primary_res['ip_list'], f'standbyro@{primary_tenant}', pwd_escaped)
            set_mode_sql = 'ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE PROTECTION tenant = %s'
            expected_mode = MAX_PROTECTION
        elif sync_mode == "availability":
            net_timeout = getattr(options, 'net_timeout', None)
            health_check_time = getattr(options, 'health_check_time', None)
            service_options = ''
            if net_timeout:
                service_options += ' NET_TIMEOUT=%s' % net_timeout
            if health_check_time:
                service_options += ' HEALTH_CHECK_TIME=%s' % health_check_time
            dest_primary = 'SERVICE=%s%s USER=%s PASSWORD=%s' % (standby_res['ip_list'], service_options, f'standbyro@{standby_tenant}', pwd_escaped)
            dest_standby = 'SERVICE=%s%s USER=%s PASSWORD=%s' % (primary_res['ip_list'], service_options, f'standbyro@{primary_tenant}', pwd_escaped)
            set_mode_sql = 'ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE AVAILABILITY tenant = %s'
            expected_mode = MAX_AVAILABILITY

        primary_tenant_id = primary_res['TENANT_ID']
        standby_tenant_id = standby_res['TENANT_ID']

        sql_max_schema = "SELECT MAX(schema_version) as max_schema FROM oceanbase.__all_virtual_ddl_operation WHERE tenant_id = %s" % primary_tenant_id

        while True:
            max_schema_res = primary_cursor.fetchone(sql_max_schema, stdio=stdio)
            if not max_schema_res or not max_schema_res.get('max_schema'):
                stdio.error('Failed to query primary tenant schema info.')
                stdio.stop_loading('fail')
                return plugin_context.return_false()
            max_schema_version = max_schema_res['max_schema']
            sql_check_schema = "SELECT COUNT(*) as cnt FROM oceanbase.__all_virtual_server_schema_info WHERE tenant_id = %s AND refreshed_schema_version < %s AND (svr_ip, svr_port) IN (SELECT svr_ip, svr_port FROM oceanbase.gv$ob_units WHERE tenant_id = %s)" % (standby_tenant_id, max_schema_version, standby_tenant_id)
            check_res = standby_cursor.fetchone(sql_check_schema, stdio=stdio)
            if check_res and check_res.get('cnt') == 0:
                break
            time.sleep(2)

        # 1. Primary: set sync standby dest to standby
        sql_primary_dest = 'ALTER SYSTEM SET SYNC_STANDBY_DEST = "%s" tenant="%s"' % (dest_primary, primary_tenant)
        if not primary_cursor.execute(sql_primary_dest, stdio=stdio):
            stdio.error('Primary set SYNC_STANDBY_DEST failed.')
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        # 2. Standby: set sync standby dest to primary
        sql_standby_dest = 'ALTER SYSTEM SET SYNC_STANDBY_DEST = "%s" tenant="%s"' % (dest_standby, standby_tenant)
        if not standby_cursor.execute(sql_standby_dest, stdio=stdio):
            stdio.error('Standby set SYNC_STANDBY_DEST failed.')
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        # 3. Wait for sync_scn gap < 5s before upgrading protection mode
        sql_sync_scn = "SELECT sync_scn FROM oceanbase.DBA_OB_TENANTS WHERE tenant_id = %s"
        while True:
            pri_scn_res = primary_cursor.fetchone(sql_sync_scn, args=(primary_tenant_id,), raise_exception=False, stdio=stdio)
            sta_scn_res = standby_cursor.fetchone(sql_sync_scn, args=(standby_tenant_id,), raise_exception=False, stdio=stdio)

            if pri_scn_res and sta_scn_res:
                pri_scn = pri_scn_res.get('sync_scn')
                sta_scn = sta_scn_res.get('sync_scn')
                if pri_scn is not None and sta_scn is not None:
                    try:
                        diff = int(pri_scn) - int(sta_scn)
                        if diff <= 5000000000:
                            break
                    except Exception as e:
                        stdio.verbose("Parse sync_scn failed: %s" % e)
            time.sleep(2)

        # 4. Primary: set standby tenant to MAXIMIZE PROTECTION / MAXIMIZE AVAILABILITY
        if not primary_cursor.execute(set_mode_sql, args=(primary_tenant,), stdio=stdio):
            stdio.error('Primary set sync mode to %s failed.' % sync_mode)
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        # time.sleep(10)

        sql = "SELECT PROTECTION_MODE FROM oceanbase.DBA_OB_TENANTS WHERE tenant_name='%s'"

        max_wait = 120
        step = 5
        synced = False
        for _ in range(0, max_wait, step):
            res_pri = primary_cursor.fetchone(sql % primary_tenant, stdio=stdio)
            res_sta = standby_cursor.fetchone(sql % standby_tenant, stdio=stdio)

            if res_pri and res_sta:
                if res_pri['PROTECTION_MODE'] == expected_mode and res_sta['PROTECTION_MODE'] == expected_mode:
                    synced = True
                    break
            time.sleep(step)

        if not synced:
            stdio.error('Verification timeout: failed to reach %s sync mode within %ds' % (expected_mode, max_wait))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()