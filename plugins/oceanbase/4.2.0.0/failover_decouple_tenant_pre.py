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

import time
from collections import defaultdict

from const import COMP_OB, COMP_OB_CE, COMPS_OB, COMP_OB_STANDALONE, SERVICE_MODE
from tool import Cursor

# Same pattern as switchover_tenant.py: cache tenant cursors on the sys-level Cursor.
tenant_cursor_cache = defaultdict(dict)


def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', raise_exception=False, retries=20):
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'
    tenant_cursor = None
    if cursor in tenant_cursor_cache and tenant in tenant_cursor_cache[cursor] and user in tenant_cursor_cache[cursor][tenant]:
        tenant_cursor = tenant_cursor_cache[cursor][tenant][user]
    else:
        query_sql = (
            "select a.SVR_IP as SVR_IP, c.SQL_PORT as SQL_PORT from oceanbase.DBA_OB_UNITS as a, "
            "oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  "
            "where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
        )
        tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
        for tenant_server_port in tenant_server_ports:
            tenant_ip = tenant_server_port['SVR_IP']
            tenant_port = tenant_server_port['SQL_PORT']
            tenant_cursor = cursor.new_cursor(
                tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, mode=mode, print_exception=raise_exception
            )
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, raise_exception=raise_exception, retries=retries - 1)
    return tenant_cursor.execute(sql, raise_exception=False, exc_level='verbose') if tenant_cursor else False


def failover_decouple_tenant_pre(plugin_context, cursors={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    cmds = plugin_context.cmds
    option_type = cmds[2]
    standby_tenant = getattr(options, 'tenant_name', '')
    if not standby_tenant:
        stdio.error('Standby tenant name is empty.')
        return False
    standby_cursor = cursors.get(standby_deploy_name)
    if not standby_cursor:
        stdio.error('standby deploy: {} connect check fail.'.format(standby_deploy_name))
        return False
    # role check
    stdio.start_loading('Check tenant')
    sql = "select TENANT_ID, TENANT_ROLE, TENANT_TYPE, STATUS, COMPATIBILITY_MODE from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    standby_info_res = standby_cursor.fetchone(sql, (standby_tenant, ), raise_exception=True)
    if not standby_info_res:
        stdio.error("Tenant:{} not exists in deployment:{}".format(standby_tenant, standby_deploy_name))
        stdio.stop_loading('fail')
        return

    plugin_context.set_variable('tenant_mode', standby_info_res['COMPATIBILITY_MODE'])

    if standby_info_res['TENANT_ROLE'] != 'STANDBY':
        stdio.error("Standby tenant {}:{}'s role is invalid, Expect: USER , Current:{}.".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_ROLE']))
        stdio.stop_loading('fail')
        return

    primary_dict = cluster_config.get_component_attr('primary_tenant')
    primary_info = primary_dict.get(standby_tenant, []) if primary_dict else []
    primary_cluster = primary_info[0][0] if primary_info else None
    primary_tenant = primary_info[0][1] if primary_info else None
    primary_cursor = cursors.get(primary_cluster) if primary_cluster else None

    if option_type == 'failover':
        source_ret = standby_cursor.fetchone("SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s", (standby_info_res['TENANT_ID'], ), raise_exception=False)
        if not source_ret:
            stdio.error("in {} tenant {} find log restore source is failed".format(standby_deploy_name, standby_tenant))
            return
        if source_ret['TYPE'] == SERVICE_MODE:
            res = standby_cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s', (standby_tenant, ), raise_exception=False)
            if not res:
                stdio.error("Query tenant {}:{}'s primary tenant info fail, place confirm current tenant is have the primary tenant.".format(standby_deploy_name, standby_tenant))
                stdio.stop_loading('fail')
                return
            primary_info_arr = res['VALUE'].split(',')
            primary_info_dict = {}
            for primary_info_item in primary_info_arr:
                kv = primary_info_item.split('=')
                primary_info_dict[kv[0]] = kv[1]
            user = primary_info_dict.get('USER')
            source_password = primary_info_dict.get('PASSWORD')
            
            comp_name = cluster_config.name
            if comp_name in (COMP_OB, COMP_OB_STANDALONE):
                standbyro_password_dict = cluster_config.get_component_attr('standbyro_password')
                tenant_standbyro_password = standbyro_password_dict.get(standby_tenant, '') if standbyro_password_dict else ''
            else:
                tenant_standbyro_password = source_password
            
            tenant_root_password = getattr(options, 'tenant_root_password', '') or ''
            
            if comp_name not in COMPS_OB:
                stdio.error('Unsupported component {} for primary tenant probe.'.format(comp_name))
                stdio.stop_loading('fail')
                return
            is_ce_ob = comp_name == COMP_OB_CE
            is_enterprise_ob = not is_ce_ob

            primary_ip_list = primary_info_dict.get('IP_LIST').split(';')
            tenant_mode = standby_info_res['COMPATIBILITY_MODE'].lower()

            for ip_list in primary_ip_list:
                ip = ip_list.split(':')[0]
                port = ip_list.split(':')[1]
                stdio.verbose('connect primary tenant server: %s -P%s -u%s' % (ip, port, user))
                tenant_name = standby_tenant
                connect_user = user or 'standbyro'
                if user and '@' in user:
                    connect_user, tenant_name = user.split('@', 1)
                normalized_user = (connect_user or '').lower()
                password = ''
                if is_ce_ob:
                    password = source_password or ''
                    if not password:
                        stdio.error('Missing PASSWORD in LOG_RESTORE_SOURCE for CE deployment; cannot probe primary tenant.')
                        stdio.stop_loading('fail')
                        return
                elif is_enterprise_ob:
                    if normalized_user == 'standbyro':
                        password = tenant_standbyro_password
                        if not password:
                            stdio.error('Missing standbyro password in inner_config for tenant {}; cannot probe primary tenant.'.format(standby_tenant))
                            stdio.stop_loading('fail')
                            return
                    elif normalized_user in ('sys', 'root'):
                        password = tenant_root_password
                        if not password:
                            stdio.error('Missing tenant root password; please retry with --tenant-root-password=xxxxxx to probe primary tenant.')
                            stdio.stop_loading('fail')
                            return
                    else:
                        stdio.error('Unsupported LOG_RESTORE_SOURCE user {} for enterprise deployment; cannot obtain password.'.format(connect_user))
                        stdio.stop_loading('fail')
                        return
                mode = tenant_mode
                probe_sql = 'select 1' if mode == 'mysql' else 'select 1 from DUAL'
                sql_user = connect_user
                if mode == 'oracle' and sql_user and sql_user.upper() == 'SYS':
                    sql_user = 'SYS'

                try:
                    # Prefer primary cluster cursor to query tenant metadata and connect tenant.
                    if primary_cursor and exec_sql_in_tenant(
                            probe_sql, primary_cursor, tenant_name, mode, user=sql_user, password=password,
                            raise_exception=False, retries=3):
                        stdio.error('Primary tenant status is alive, not support failover.')
                        stdio.stop_loading('fail')
                        return
                    if not primary_cursor:
                        direct_cursor = Cursor(
                            ip=ip, port=port, user=sql_user, tenant=tenant_name, password=password, mode=mode, stdio=stdio
                        )
                        if direct_cursor.execute(probe_sql, raise_exception=False, exc_level='verbose'):
                            stdio.error('Primary tenant status is alive, not support failover.')
                            stdio.stop_loading('fail')
                            return
                except:
                    pass
        else:
            if primary_cursor and primary_tenant:
                sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME='%s'" % primary_tenant
                res = primary_cursor.fetchone(sql)
                if res:
                    stdio.error('Primary tenant status is alive, not support failover.')
                    stdio.stop_loading('fail')
                    return
    # check tenant type
    if standby_info_res['TENANT_TYPE'] != 'USER':
        stdio.error("Standby tenant {}:{}'s type is invalid, Expect: USER , Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_TYPE']))
        stdio.stop_loading('fail')
        return

    # check tenant status
    if standby_info_res['STATUS'] != 'NORMAL':
        stdio.error("Standby tenant {}:{}'s status is invalid, Expect: NORMAL , Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['STATUS']))
        stdio.stop_loading('fail')
        return

    # check log stream has no leader
    sql = " SELECT COUNT(1) as `count` FROM oceanbase.CDB_OB_LS A LEFT JOIN oceanbase.GV$OB_LOG_STAT B ON A.LS_ID = B.LS_ID AND A.TENANT_ID = B.TENANT_ID  AND B.ROLE='LEADER' WHERE B.LS_ID IS NULL AND A.STATUS NOT IN ('CREATING', 'CREATED', 'TENANT_DROPPING', 'CREATE_ABORT', 'PRE_TENANT_DROPPING') AND A.TENANT_ID IN (%s,%s)"
    no_leader_log_stream = standby_cursor.fetchone(sql, (standby_info_res['TENANT_ID'], int(standby_info_res['TENANT_ID']) - 1), raise_exception=True)
    if no_leader_log_stream['count'] != 0:
        stdio.error("Standby tenant {}:{} has log stream no leader".format(standby_deploy_name, standby_tenant))
        stdio.stop_loading('fail')
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
