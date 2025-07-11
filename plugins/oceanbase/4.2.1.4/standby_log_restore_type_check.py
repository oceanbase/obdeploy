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
from const import LOCATION_MODE

def standby_log_restore_type_check(plugin_context, cluster_configs, cursors={}, relation_tenants={}, *args, **kwargs):
    def get_primary_tenant(standby_cursor, standby_cluster_name, standby_tenant_name):
        standby_cluster = cluster_configs.get(standby_cluster_name)
        primary_dict = standby_cluster.get_component_attr('primary_tenant')
        if primary_dict:
            primary_info = primary_dict.get(standby_tenant_name, [])
            if primary_info:
                return primary_info[0][0], primary_info[0][1]
        res = standby_cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s ', (standby_tenant_name,), raise_exception=False)
        if not res:
            stdio.error("Query tenant {}:{}'s primary tenant info fail, place confirm current tenant is have the primary tenant.".format(standby_cluster_name, standby_tenant_name))
            return

        primary_info_dict = {}
        primary_info_arr = res['VALUE'].split(',')
        for primary_info in primary_info_arr:
            kv = primary_info.split('=')
            primary_info_dict[kv[0]] = kv[1]
        primary_ip_list = primary_info_dict.get('IP_LIST').split(';')
        primary_ip_list.sort()
        primary_tenant_id = int(primary_info_dict['TENANT_ID']) if primary_info_dict else None
        for relation_kv in relation_tenants:
            relation_deploy_name = relation_kv[0]
            relation_tenant_name = relation_kv[1]
            relation_cursor = cursors.get(relation_deploy_name)
            if not relation_cursor:
                stdio.verbose("fail to get {}'s cursor".format(relation_deploy_name))
                continue

            res = relation_cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (relation_tenant_name, ), raise_exception=True)
            if not res or not res['ip_list']:
                stdio.verbose("fail to get {}'s ip list".format(relation_deploy_name))
                continue

            ip_list = res['ip_list'].split(';')
            ip_list.sort()
            if res['TENANT_ID'] == primary_tenant_id and ip_list == primary_ip_list:
                return relation_deploy_name, relation_tenant_name

    def error(msg='', *arg, **kwargs):
        stdio.stop_loading('failed')
        stdio.error(msg)
        

    options = plugin_context.options
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds

    cluster_name = cmds[0]
    tenant_name = cmds[1]
    cursor = cursors.get(cluster_name)
    if not cursor:
        error(f"get {cluster_name} cursor is failed")
        return
    stdio.start_loading("source type check")
    sql = 'select TENANT_ID,TENANT_ROLE from oceanbase.DBA_OB_TENANTS where tenant_name=%s'
    res = cursor.fetchone(sql, (tenant_name, ))
    if not res or res['TENANT_ID'] is None:
        error(f"Tenant {cluster_name}:{tenant_name} is not exist.")
        return
    tenant_id = res['TENANT_ID']
    if res['TENANT_ROLE'] == 'PRIMARY':
        error(f'Tenant role {cluster_name}:{tenant_name} is PRIMARY. Unable to perform the current operation.')
        return

    sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s'
    res = cursor.fetchone(sql, (tenant_id, ))
    if not res or res['TYPE'] is None:
        error(f"{cluster_name}:{tenant_name} log recovery source does not exist. Unable to perform the current operation.")
        return
    plugin_context.set_variable("source_type", res['TYPE'])

    log_source_type = None
    if kwargs.get('option_mode') == 'log_source':
        primary_deploy, primary_tenant = get_primary_tenant(cursor, cluster_name, tenant_name)
        primary_cursor = cursors.get(primary_deploy)
        plugin_context.set_variable("primary_cursor", primary_cursor)
        primary_res = primary_cursor.fetchone('select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (primary_tenant, ), raise_exception=False)
        plugin_context.set_variable("primary_tenant_id", primary_res['TENANT_ID'])
        plugin_context.set_variable("primary_tenant", primary_tenant)
        log_source_type = get_option(options, 'type')
    if res['TYPE'] == log_source_type:
        error("Current and target log recovery sources are identical.")
        return

    if kwargs.get('option_mode') == 'switchover_tenant':
        if res['TYPE'] == LOCATION_MODE:
            sql = 'SELECT SYNC_STATUS FROM oceanbase.v$ob_ls_log_restore_status WHERE TENANT_ID=%s'
            res = cursor.fetchone(sql, (tenant_id, ))
            if not res and res['SYNC_STATUS'] is None:
                error(f"select {cluster_name}:{tenant_name} sync_status is failed")
                return
            sync_status = res['SYNC_STATUS']
            if sync_status != 'NORMAL':
                if sync_status == 'RESTORE SUSPEND':
                    error(err.EC_OBSERVER_LOG_RECOVER.format(cluster_name=cluster_name, tenant_name=tenant_name))
                    return
                
                error(f"The {cluster_name}:{tenant_name} log stream {sync_status} status is unexpected")
                return
            primary_deploy, primary_tenant = get_primary_tenant(cursor, cluster_name, tenant_name)
        else:
            primary_deploy, primary_tenant = get_primary_tenant(cursor, cluster_name, tenant_name)
            if not primary_deploy or not primary_tenant:
                error(f"get {cluster_name}:{tenant_name} primary tenant is failed")
                return
            for relation_tenant in relation_tenants:
                relation_deploy_name = relation_tenant[0]
                relation_tenant_name = relation_tenant[1]
                cursor = cursors.get(relation_deploy_name)
                if not cursor:
                    stdio.error("Connect to {} failed.".format(relation_deploy_name))
                    return
                res = cursor.fetchone('select TENANT_ROLE,TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (relation_tenant_name,), raise_exception=False)
                if not res:
                    return
                if res['TENANT_ROLE'] == 'PRIMARY':
                    continue
                sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % res['TENANT_ID']
                res = cursor.fetchone(sql, raise_exception=False)
                if not res:
                    stdio.verbose('Select {} log restore source is failed.'.format(relation_deploy_name))
                    continue
                relation_primary_cluster, relation_primary_tenant = get_primary_tenant(cursor, relation_deploy_name, relation_tenant_name)

                if res['TYPE'] == LOCATION_MODE:
                    if relation_primary_cluster == primary_deploy and relation_primary_tenant == primary_tenant:
                        plugin_context.set_variable("check_tenant_id", tenant_id)
                        plugin_context.set_variable("check_uri", True)
                        standby_cursor = cursors.get(cluster_name)
                        plugin_context.set_variable("check_tenant_cursor", standby_cursor)
                        plugin_context.set_variable('check_tenant', tenant_name)
                        break
                    elif relation_primary_cluster == cluster_name and relation_primary_tenant == tenant_name:
                        primary_cursor = cursors.get(primary_deploy)
                        res = primary_cursor.fetchone('select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (primary_tenant, ), raise_exception=False)
                        plugin_context.set_variable("check_tenant_id", res['TENANT_ID'])
                        plugin_context.set_variable("check_uri", True)
                        plugin_context.set_variable("check_tenant_cursor", primary_cursor)
                        plugin_context.set_variable('check_tenant', primary_tenant)
                        break
        primary_cursor = cursors.get(primary_deploy)
        res = primary_cursor.fetchone('select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (primary_tenant,), raise_exception=False)
        plugin_context.set_variable("primary_tenant_id", res['TENANT_ID'])
        plugin_context.set_variable("primary_tenant_cursor", primary_cursor)
        plugin_context.set_variable('primary_tenant', primary_tenant)


    stdio.stop_loading("succeed")
    return plugin_context.return_true()
