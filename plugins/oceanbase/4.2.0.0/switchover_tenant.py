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

global_standbyro_user_passord = None
max_delay_time = 5000
RECOVERY_UNTIL_SCN = 4611686018427387903
tenant_cursor_cache = defaultdict(dict)


def get_standbyro_password(deploy_name, tenant_name, cluster_config, get_option, stdio):
    standbyro_password_input = get_option('standbyro_password', '')
    if standbyro_password_input:
        return standbyro_password_input
    if not cluster_config:
        stdio.error('No such deploy: %s.' % deploy_name)
        return False
    standbyro_password = cluster_config.get_component_attr('standbyro_password')
    return standbyro_password.get(tenant_name, '') if standbyro_password else ''


def get_ip_list(cursor, deploy_name, tenant, stdio):
    if not cursor:
        stdio.verbose('Get ip list error: failed to connect {}.'.format(deploy_name))
        return
    res = cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (tenant, ), raise_exception=False)
    if not res:
        stdio.error('{}:{} not exist.'.format(deploy_name, tenant))
        return
    return res['ip_list']


def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', raise_exception=False, retries=20):
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'
    # find tenant ip, port
    tenant_cursor = None
    if cursor in tenant_cursor_cache and tenant in tenant_cursor_cache[cursor] and user in tenant_cursor_cache[cursor][tenant]:
        tenant_cursor = tenant_cursor_cache[cursor][tenant][user]
    else:
        query_sql = "select a.SVR_IP as SVR_IP, c.SQL_PORT as SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
        tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
        for tenant_server_port in tenant_server_ports:
            tenant_ip = tenant_server_port['SVR_IP']
            tenant_port = tenant_server_port['SQL_PORT']
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, print_exception=raise_exception)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, raise_exception=raise_exception, retries=retries - 1)
    return tenant_cursor.execute(sql, raise_exception=False, exc_level='verbose') if tenant_cursor else False


def verify_password(cursor, tenant_name, stdio, key, password='', user='root', mode='mysql'):
    if exec_sql_in_tenant('select 1', cursor, tenant_name, mode, user=user, password=password, raise_exception=False, retries=5):
        return True
    if key == 'standbyro_password':
        key = 'standbyro-password'
    stdio.error("Authentication failed, no valid password for {}:{}. please retry with '--{}=xxxxxx'".format(tenant_name, user, key))
    return False


def switchover_tenant(plugin_context, cluster_configs, cursors={}, primary_info={}, *args, **kwargs):
    def error(msg='', *arg, **kwargs):
        msg and stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('fail') 
        
    def exception(msg='', *arg, **kwargs):
        stdio.exception(msg=msg, *arg, **kwargs)
        stdio.stop_loading('fail')

    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value

    def call_plugin(plugin, *args, **kwargs):
        return plugin(plugin_context.namespace, plugin_context.namespaces, plugin_context.deploy_name, plugin_context.deploy_status,
            plugin_context.repositories, plugin_context.components, plugin_context.clients,
            plugin_context.cluster_config, plugin_context.cmds, plugin_context.options,
            plugin_context.stdio, *args, **kwargs)

    stdio = plugin_context.stdio
    options = plugin_context.options
    repositories = plugin_context.repositories
    standby_tenant = getattr(options, 'tenant_name', '')
    if not cursors:
        error("Connect to OceanBase failed.")
        return
    primary_deploy_name = primary_info.get('primary_deploy_name')
    primary_tenant = primary_info.get('primary_tenant')
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    primary_cursor = cursors.get(primary_deploy_name)
    standby_cursor = cursors.get(standby_deploy_name)
    primary_cluster_config = cluster_configs[primary_deploy_name]
    standbyro_password = get_standbyro_password(primary_deploy_name, primary_tenant, primary_cluster_config, get_option, stdio)

    # find primary and standby tenant`s others relationship
    stdio.start_loading('Find relationship')
    # 1.find primary tenant`s others standby tenant
    plugin_manager = kwargs.get('plugin_manager')
    for repository in repositories:
        get_standbys_plugin = plugin_manager.get_best_py_script_plugin('get_standbys', repository.name, repository.version)
        ret = call_plugin(get_standbys_plugin, primary_deploy_name=primary_deploy_name, primary_tenant=primary_tenant, exclude_tenant=[standby_deploy_name, standby_tenant])
        if not ret:
            error("Find primary tenant {}:{}'s others standby tenants failed".format(primary_deploy_name, primary_tenant))
            return
    primary_standby_tenants = ret.get_return('standby_tenants')
    stdio.verbose("Primary tenant {}:{}'s others standby tenants:{}".format(primary_deploy_name, primary_tenant, primary_standby_tenants))
    # 2.find standby tenant`s standby tenant
    for repository in repositories:
        get_standbys_plugin = plugin_manager.get_best_py_script_plugin('get_standbys', repository.name, repository.version)
        ret = call_plugin(get_standbys_plugin, primary_deploy_name=standby_deploy_name, primary_tenant=standby_tenant, exclude_tenant=[primary_deploy_name, primary_tenant])
        if not ret:
            error("Find standby tenant {}:{}'s others standby tenants failed".format(standby_deploy_name, standby_tenant))
            return
    standby_standby_tenants = ret.get_return('standby_tenants')
    stdio.verbose("Standby tenant {}:{}'s others standby tenants:{}".format(standby_deploy_name, standby_tenant, standby_standby_tenants))
    stdio.stop_loading('succeed')

    stdio.start_loading('Validate tenant status')
    sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    standby_info_res = standby_cursor.fetchone(sql, (standby_tenant, ))
    if not standby_info_res:
        error("Tenant {}:{} not exists".format(standby_deploy_name, standby_tenant))
        return
    primary_res = primary_cursor.fetchone(sql, [primary_tenant, ])
    if not primary_res:
        error("Primary tenant {}:{} not exists".format(primary_deploy_name, primary_tenant))
        return

    # check tenant role
    if standby_info_res['TENANT_ROLE'] != 'STANDBY':
        error("Standby tenant {}:{}'s role is invalid, Expect: STANDBY , Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_ROLE']))
        return
    if primary_res['TENANT_ROLE'] != 'PRIMARY':
        error("Srimary tenant {}:{}'s role is invalid,current not support non-primary tenant as primary to switchover. ".format(standby_deploy_name, primary_tenant))
        return

    # check tenant status
    if standby_info_res['STATUS'] != 'NORMAL':
        error("Standby tenant {}:{}'s status is invalid, Expect: NORMAL, Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['STATUS']))
        return
    if primary_res['STATUS'] != 'NORMAL':
        error("Primarytenant {}:{}'s status is invalid, Expect: NORMAL, Current:{}".format(primary_deploy_name, primary_tenant, primary_res['STATUS']))
        return

    # check primary standby switchover status
    if standby_info_res['SWITCHOVER_STATUS'] != 'NORMAL':
        error("standby tenant {}:{}'s switchover status is invalid, Expect: NORMAL, Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['SWITCHOVER_STATUS']))
        return
    if primary_res['SWITCHOVER_STATUS'] != 'NORMAL':
        error("primary tenant {}:{}'s switchover status is invalid, Expect: NORMAL, Current:{}".format(primary_deploy_name, primary_tenant, primary_res['SWITCHOVER_STATUS']))
        return

    # check tenant type
    if standby_info_res['TENANT_TYPE'] != 'USER':
        error("standby tenant {}:{}'s type is invalid, Expect: USER, Current:{}".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_TYPE']))
        return
    if primary_res['TENANT_TYPE'] != 'USER':
        error("primary tenant {}:{}'s type is invalid, Expect: USER, Current:{}".format(primary_deploy_name, primary_tenant, primary_res['TENANT_TYPE'] != 'USER'))
        return

    # check primary tenant recover until scn
    if primary_res['RECOVERY_UNTIL_SCN'] != RECOVERY_UNTIL_SCN:
        error("primary tenant {}:{}'s recover_until_scn not unlimited".format(primary_deploy_name, primary_tenant))
        return

    # check log stream has no leader
    sql = " SELECT COUNT(1) as `count` FROM oceanbase.CDB_OB_LS A LEFT JOIN oceanbase.GV$OB_LOG_STAT B ON A.LS_ID = B.LS_ID AND A.TENANT_ID = B.TENANT_ID  AND B.ROLE='LEADER' WHERE B.LS_ID IS NULL AND A.STATUS NOT IN ('CREATING', 'CREATED', 'TENANT_DROPPING', 'CREATE_ABORT', 'PRE_TENANT_DROPPING') AND A.TENANT_ID IN (%s,%s)"
    no_leader_log_stream = standby_cursor.fetchone(sql, (standby_info_res['TENANT_ID'], int(standby_info_res['TENANT_ID']) - 1), raise_exception=True)
    if no_leader_log_stream.get('count') != 0:
        error("standby tenant {} has log stream no leader".format(standby_tenant))
        return
    no_leader_log_stream = primary_cursor.fetchone(sql, (standby_info_res['TENANT_ID'], int(standby_info_res['TENANT_ID']) - 1), raise_exception=True)
    if no_leader_log_stream.get('count') != 0:
        error("primary tenant {} has log stream no leader".format(primary_tenant))
        return

    # check standby tenant synchronization delay cannot be greater than the threshold:5s.
    startTime = round(time.time() * 1000)
    if primary_res['TENANT_ROLE'] == 'PRIMARY':
        sql = "SELECT end_scn FROM oceanbase.GV$OB_LOG_STAT WHERE tenant_id = %s AND ls_id = 1 AND role = 'leader'"
        primary_end_scn = primary_cursor.fetchone(sql, (primary_res['TENANT_ID'], ), raise_exception=True)
        if not primary_end_scn:
            error("query primary tenant {}'s info for calculate standby tenant {} sync delay time failed".format(primary_tenant, standby_tenant))
            return
        query_time = round(time.time() * 1000) - startTime
        delay_time = (primary_end_scn['end_scn'] - standby_info_res['SYNC_SCN']) / 1000000 - query_time
        stdio.verbose("primary {} sysLsEndScn={}, standby {} syncScn={}, sql query time is {}ms, sync delay time is {}ms".format(primary_tenant, primary_end_scn.get('end_scn'), standby_tenant, standby_info_res['SYNC_SCN'], query_time, delay_time))

    else:
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
            error("Standby tenant {}:{} synchronization delay:{}ms is greater than the threshold:{}ms, place retry when delay < {} ".format(standby_deploy_name, standby_tenant, delay_time, max_delay_time, max_delay_time))
            return

    # check tenant transform status is normal
    sql = "SELECT tenant_id, ls_id, sync_lsn, sync_scn, REPLACE(`sync_status`, ' ', '_') as sync_status, err_code, comment FROM oceanbase.V$OB_LS_LOG_RESTORE_STATUS WHERE sync_status != 'NORMAL' AND tenant_id = %s"
    transform_abnormal_status = standby_cursor.fetchone(sql, (standby_info_res['TENANT_ID'], ), raise_exception=True)
    if transform_abnormal_status:
        error("Standby tenant {} transform status is abnormal".format(standby_tenant))
        return
    # 0. do password verify
    primary_tenant_password = getattr(plugin_context.options, 'tenant_root_password') if getattr(plugin_context.options, 'tenant_root_password') else ''
    standby_tenant_password = getattr(plugin_context.options, 'tenant_root_password') if getattr(plugin_context.options, 'tenant_root_password') else ''

    if not verify_password(primary_cursor, primary_tenant, stdio, key='tenant-root-password', password=primary_tenant_password):
        stdio.stop_loading('fail')
        return
    if not verify_password(standby_cursor, standby_tenant, stdio, key='standbyro_password', password=standbyro_password, user='standbyro'):
        stdio.stop_loading('fail')
        return
    if not verify_password(standby_cursor, standby_tenant, stdio, key='tenant-root-password', password=standby_tenant_password):
        stdio.stop_loading('fail')
        return
    if not verify_password(primary_cursor, primary_tenant, stdio, key='standbyro_password', password=standbyro_password, user='standbyro'):
        stdio.stop_loading('fail')
        return

    # 1.do ob inner switchover verify
    try:
        sql = "ALTER SYSTEM SWITCHOVER TO STANDBY VERIFY"
        exec_sql_in_tenant(sql, primary_cursor, primary_tenant, mode='mysql', user='root', password=primary_tenant_password, raise_exception=True, retries=5)
    except Exception as e:
        exception("Primary tenant {}:{} do switchover verify failed:{}".format(primary_deploy_name, primary_tenant, e))
        return

    try:
        sql = "ALTER SYSTEM SWITCHOVER TO PRIMARY VERIFY"
        exec_sql_in_tenant(sql, standby_cursor, standby_tenant, mode='mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=5)
    except Exception as e:
        exception("Standby tenant {}:{} do switchover verify failed:{}".format(standby_deploy_name, standby_tenant, e))
        return
    stdio.stop_loading('succeed')

    stdio.start_loading('Switchover')

    # 2. switchover primary tenant to standby tenant
    stdio.verbose("begin switchover primary tenant to standby tenant on the tenant {}:{}".format(primary_deploy_name, primary_tenant))
    try:
        sql = "ALTER SYSTEM SWITCHOVER TO STANDBY"
        exec_sql_in_tenant(sql, primary_cursor, primary_tenant, mode='mysql', user='root', password=primary_tenant_password, raise_exception=True, retries=5)
    except Exception as e:
        exception("Switchover primary tenant {} to standby tenant {} failed. error message info:{}".format(primary_tenant, standby_tenant, e))
        return
    stdio.verbose("switchover primary tenant to standby tenant succeed on the tenant {}:{}".format(primary_deploy_name, primary_tenant))

    # 3. switch standby tenant to primary tenant
    stdio.verbose("begin switchover standby tenant to primary tenant on the tenant {}:{}".format(standby_deploy_name, standby_tenant))
    try:
        sql = "ALTER SYSTEM SWITCHOVER TO PRIMARY"
        exec_sql_in_tenant(sql, standby_cursor, standby_tenant, mode='mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=5)
    except Exception as e:
        exception("Switchover standby tenant {} to primary tenant {} failed. error message info:{}".format(standby_tenant, primary_tenant, e))
        return
    stdio.verbose("switchover standby tenant to primary tenant succeed on the tenant {}:{}".format(standby_deploy_name, standby_tenant))
    stdio.stop_loading('succeed')

    # 4. set log restore source for the new standby tenant
    stdio.start_loading('Set log restore source')
    ip_list = get_ip_list(standby_cursor, standby_deploy_name, standby_tenant, stdio)
    if not ip_list:
        stdio.error("Get the ip list of the tenant {}:{} failed.".format(standby_deploy_name, standby_tenant))
        return
    sql = 'ALTER SYSTEM SET LOG_RESTORE_SOURCE = "SERVICE={} USER=standbyro@{} PASSWORD={}"'.format(ip_list, standby_tenant, standbyro_password)
    try:
        exec_sql_in_tenant(sql, primary_cursor, primary_tenant, 'mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=5)
        stdio.stop_loading('succeed')
    except Exception as e:
        retry_message = 'After resolving the issue, you can retry by manually executing SQL:\'{}\' with the root user in the tenant {}:{}.'.format(sql, primary_deploy_name, primary_tenant)
        exception("Set the new standby tenant {}:{}'s log restore to {}:{} failed:{}. \n {}".format(primary_deploy_name, primary_tenant, standby_deploy_name, standby_tenant, e, retry_message))


    plugin_context.set_variable('old_primary_standby_tenants', primary_standby_tenants)
    plugin_context.set_variable('old_standby_standby_tenants', standby_standby_tenants)

    return plugin_context.return_true()
