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
import sys

if sys.version_info.major == 2:
    import MySQLdb as mysql

    def connect(ip, port, user, password):
        db = mysql.connect(host=ip, user=user, port=int(port), passwd=str(password))
        return db.cursor(cursorclass=mysql.cursors.DictCursor)

else:
    import pymysql as mysql

    def connect(ip, port, user, password):
        db = mysql.connect(host=ip, user=user, port=int(port), password=str(password), cursorclass=mysql.cursors.DictCursor)
        return db.cursor()


def failover_decouple_tenant_pre(plugin_context, cursors={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
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
    sql = "select TENANT_ID, TENANT_ROLE, TENANT_TYPE, STATUS from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    standby_info_res = standby_cursor.fetchone(sql, (standby_tenant, ), raise_exception=True)
    if not standby_info_res:
        stdio.error("Tenant:{} not exists in deployment:{}".format(standby_tenant, standby_deploy_name))
        stdio.stop_loading('fail')
        return
    if standby_info_res['TENANT_ROLE'] != 'STANDBY':
        stdio.error("Standby tenant {}:{}'s role is invalid, Expect: USER , Current:{}.".format(standby_deploy_name, standby_tenant, standby_info_res['TENANT_ROLE']))
        stdio.stop_loading('fail')
        return

        # query primary tenant connect info
    if option_type == 'failover':
        res = standby_cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s', (standby_tenant, ), raise_exception=False)
        if not res:
            stdio.error("Query tenant {}:{}'s primary tenant info fail, place confirm current tenant is have the primary tenant.".format(standby_deploy_name, standby_tenant))
            stdio.stop_loading('fail')
            return
        primary_info_arr = res['VALUE'].split(',')
        primary_info_dict = {}
        for primary_info in primary_info_arr:
            kv = primary_info.split('=')
            primary_info_dict[kv[0]] = kv[1]
        user = primary_info_dict.get('USER')
        password = primary_info_dict.get('PASSWORD')
        primary_ip_list = primary_info_dict.get('IP_LIST').split(';')

        for ip_list in primary_ip_list:
            ip = ip_list.split(':')[0]
            port = ip_list.split(':')[1]
            stdio.verbose('connect primary tenant server: %s -P%s -u%s -p%s' % (ip, port, user, password))
            try:
                db_cursor = connect(ip, port, user, password)
                db_cursor.execute('select * from oceanbase.DBA_OB_TENANTS')
                stdio.error('Primary tenant status is alive, not support failover.')
                stdio.stop_loading('fail')
                return
            except:
                pass
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
