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

def _get_tenant_role(cursor, tenant_name):
    sql = "SELECT TENANT_ROLE FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
    res = cursor.fetchone(sql, (tenant_name,), raise_exception=False)
    return res['TENANT_ROLE'] if res else None


def _get_log_restore_source(cursor, tenant_name):
    sql = 'select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s'
    res = cursor.fetchone(sql, (tenant_name,), raise_exception=False)
    return res['VALUE'] if res else None


def _get_sync_scn(cursor, tenant_name):
    sql = "SELECT SYNC_SCN FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
    res = cursor.fetchone(sql, (tenant_name,), raise_exception=False)
    return res['SYNC_SCN'] if res else None


def _get_primary_end_scn(cursor, tenant_name):
    # Get tenant_id
    sql_tid = "SELECT TENANT_ID FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
    res_tid = cursor.fetchone(sql_tid, (tenant_name,), raise_exception=False)
    if not res_tid:
        return None
    tenant_id = res_tid['TENANT_ID']
    
    # Get end_scn from GV$OB_LOG_STAT for ls_id=1 role=leader
    sql = "SELECT end_scn FROM oceanbase.GV$OB_LOG_STAT WHERE tenant_id = %s AND ls_id = 1 AND role = 'leader'"
    res = cursor.fetchone(sql, (tenant_id,), raise_exception=False)
    return res['end_scn'] if res else None


def set_sync_mode_pre(plugin_context, cursors=None, cluster_configs=None, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    cmds = plugin_context.cmds
    
    standby_deploy_name = cmds[0]
    standby_tenant_name = cmds[1]
    sync_mode = (getattr(options, 'sync_mode', None) or 'performance').strip().lower()
    net_timeout = getattr(options, 'net_timeout', None)
    health_check_time = getattr(options, 'health_check_time', None)


    if sync_mode not in ('performance', 'availability', 'protection'):
        stdio.error("Invalid mode: %s. Supported modes: performance, availability, protection." % sync_mode)
        return plugin_context.return_false()

    if sync_mode != 'availability' and (net_timeout is not None or health_check_time is not None):
        stdio.warn("The parameters --net-timeout and --health-check-time only take effect when --sync-mode=availability.")
    elif sync_mode == 'availability':
        if net_timeout is not None and (net_timeout < 10 or net_timeout > 1200):
            stdio.error("The parameter net_timeout must be between [10, 1200]. Please provide a valid value.")
            return plugin_context.return_false()
        if health_check_time is not None and health_check_time < 0:
            stdio.error("The parameter health_check_time must be greater than 0. Please provide a valid value.")
            return plugin_context.return_false()

    standby_cursor = cursors.get(standby_deploy_name)
    if not standby_cursor:
        stdio.error("Failed to connect to standby cluster: %s" % standby_deploy_name)
        return plugin_context.return_false()
    
    sql_tid = "SELECT TENANT_ID FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
    res_tid = standby_cursor.fetchone(sql_tid, (standby_tenant_name,), raise_exception=False)
    if not res_tid:
        stdio.error("Tenant %s not found in %s" % (standby_tenant_name, standby_deploy_name))
        return plugin_context.return_false()
    
    tenant_id = res_tid['TENANT_ID']
    sql_type = "SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE WHERE TENANT_ID=%s"
    res_type = standby_cursor.fetchone(sql_type, (tenant_id,), raise_exception=False)
    if not res_type or res_type['TYPE'] != 'SERVICE':
        stdio.error("Standby tenant %s is not in SERVICE mode. Current TYPE is %s." % (standby_tenant_name, res_type['TYPE'] if res_type else 'Unknown'))
        return plugin_context.return_false()
    
    # 1. Confirm standby tenant exists and is STANDBY role
    role = _get_tenant_role(standby_cursor, standby_tenant_name)
    if not role:
        stdio.error("Tenant %s not found in %s" % (standby_tenant_name, standby_deploy_name))
        return plugin_context.return_false()
    if role != 'STANDBY':
        stdio.error("Tenant %s in %s is not a STANDBY tenant (current role: %s)" % (standby_tenant_name, standby_deploy_name, role))
        return plugin_context.return_false()

    # 2. Confirm standby is not cascading (upstream must be PRIMARY)
    # Check LOG_RESTORE_SOURCE or CDB_OB_LOG_RESTORE_SOURCE
    # Format: SERVICE=ip:port;ip:port USER=...
    # We need to find the upstream cluster.
    # Logic: Get restore source, parse IP, find which deploy has that IP.
    restore_source = _get_log_restore_source(standby_cursor, standby_tenant_name)
    if not restore_source:
        stdio.error("Failed to get LOG_RESTORE_SOURCE for %s" % standby_tenant_name)
        return plugin_context.return_false()

    primary_info_dict = {}
    try:
        primary_info_arr = restore_source.split(',')
        for primary_info in primary_info_arr:
            kv = primary_info.split('=')
            if len(kv) == 2:
                primary_info_dict[kv[0]] = kv[1]
    except Exception as e:
        stdio.error("Failed to parse LOG_RESTORE_SOURCE: %s" % restore_source)
        return plugin_context.return_false()

    primary_ip_list_raw = primary_info_dict.get('IP_LIST', '').split(';')
    primary_ip_list = [ip.split('+')[0] for ip in primary_ip_list_raw if ip]
    primary_ip_list.sort()
    primary_tenant_id = int(primary_info_dict['TENANT_ID']) if primary_info_dict.get('TENANT_ID') else None

    relation_tenants = plugin_context.get_variable('relation_tenants') or []
    primary_deploy_name = None
    primary_tenant_name = None
    primary_cursor = None

    for relation_kv in relation_tenants:
        relation_deploy_name = relation_kv[0]
        relation_tenant_name = relation_kv[1]
        relation_cursor = cursors.get(relation_deploy_name)
        if not relation_cursor:
            stdio.verbose("fail to get {}'s cursor".format(relation_deploy_name))
            continue

        res = relation_cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (relation_tenant_name, ), raise_exception=False)
        if not res or not res['ip_list']:
            stdio.verbose("fail to get {}'s ip list".format(relation_deploy_name))
            continue

        ip_list = res['ip_list'].split(';')
        ip_list.sort()
        if res['TENANT_ID'] == primary_tenant_id and ip_list == primary_ip_list:
            primary_deploy_name = relation_deploy_name
            primary_tenant_name = relation_tenant_name
            primary_cursor = relation_cursor
            break

    if not primary_deploy_name:
        stdio.error("Could not find the primary cluster for standby %s. Ensure the primary cluster is deployed and managed by obd." % standby_tenant_name)
        return plugin_context.return_false()

    primary_role = _get_tenant_role(primary_cursor, primary_tenant_name)
    if not primary_role:
         stdio.error("Primary tenant %s not found in %s" % (primary_tenant_name, primary_deploy_name))
         return plugin_context.return_false()
    
    if primary_role != 'PRIMARY':
        stdio.error("Upstream tenant %s in %s is not PRIMARY (current role: %s). Cascading standby configuration is not supported for this operation." % (primary_tenant_name, primary_deploy_name, primary_role))
        return plugin_context.return_false()

    # 4. Check sync latency < 5s
    # Primary END_SCN - Standby SYNC_SCN
    startTime = round(time.time() * 1000)
    prim_end_scn = _get_primary_end_scn(primary_cursor, primary_tenant_name)
    stby_sync_scn = _get_sync_scn(standby_cursor, standby_tenant_name)
    
    if prim_end_scn and stby_sync_scn:
        # Calculate delay in ms
        # SCN is uint64.
        query_time = round(time.time() * 1000) - startTime
        diff_ns = int(prim_end_scn) - int(stby_sync_scn)
        diff_ms = diff_ns / 1000000 - query_time
        if diff_ms > 5000:
             stdio.error("Sync latency is too high: %.2f ms (threshold: 5000 ms). Please wait for synchronization to catch up." % diff_ms)
             return plugin_context.return_false()
    else:
        stdio.error("Could not retrieve SCNs to verify latency. Cannot proceed without verifying synchronization.")
        return plugin_context.return_false()

    # Pass necessary info to next stage
    plugin_context.set_variable('primary_deploy_name', primary_deploy_name)
    plugin_context.set_variable('primary_tenant_name', primary_tenant_name)
    plugin_context.set_variable('standby_deploy_name', standby_deploy_name)
    plugin_context.set_variable('standby_tenant_name', standby_tenant_name)
    
    return plugin_context.return_true()
