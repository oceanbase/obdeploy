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
from _deploy import ObserverIdentity, ObserverIdentityError

def standby_log_restore_type_check(plugin_context, cluster_configs, cursors=None, relation_tenants=None, *args, **kwargs):
    cursors = {} if cursors is None else cursors
    relation_tenants = [] if relation_tenants is None else relation_tenants

    def get_primary_tenant(standby_cursor, standby_cluster_name, standby_tenant_name, source_type):
        standby_cluster = cluster_configs.get(standby_cluster_name)
        if not standby_cluster:
            stdio.error('Get {} cluster config failed.'.format(standby_cluster_name))
            return
        if source_type == LOCATION_MODE:
            primary_dict = standby_cluster.get_component_attr('primary_tenant')
            primary_info = primary_dict.get(standby_tenant_name, []) if primary_dict else []
            if not primary_info:
                stdio.error(
                    'Cannot resolve a LOCATION source without a persisted primary_tenant mapping.')
                return
            mapped_primary = (primary_info[0][0], primary_info[0][1])
            if mapped_primary not in relation_tenants or mapped_primary[0] not in cluster_configs:
                stdio.error(
                    'The persisted primary_tenant mapping for {}:{} is invalid.'.format(
                        standby_cluster_name, standby_tenant_name))
                return
            return mapped_primary
        res = standby_cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s ', (standby_tenant_name,), raise_exception=False)
        if not res:
            stdio.error("Query tenant {}:{}'s primary tenant info fail, place confirm current tenant is have the primary tenant.".format(standby_cluster_name, standby_tenant_name))
            return

        primary_info_dict = {}
        for item in res['VALUE'].split(','):
            key, separator, value = item.partition('=')
            if separator:
                primary_info_dict[key] = value
        primary_ip_list_value = primary_info_dict.get('IP_LIST')
        primary_tenant_id_value = primary_info_dict.get('TENANT_ID')
        if not primary_ip_list_value or not primary_tenant_id_value:
            stdio.error('Invalid SERVICE LOG_RESTORE_SOURCE for tenant {}:{}.'.format(
                standby_cluster_name, standby_tenant_name))
            return
        primary_ip_list_raw = primary_ip_list_value.split(';')
        primary_tenant_id = int(primary_tenant_id_value)
        source_is_loopback = any(
            endpoint.split('+', 1)[0].rpartition(':')[0] == '127.0.0.1'
            for endpoint in primary_ip_list_raw)

        candidates = relation_tenants
        if source_is_loopback:
            primary_dict = standby_cluster.get_component_attr('primary_tenant')
            primary_info = primary_dict.get(standby_tenant_name, []) if primary_dict else []
            if not primary_info:
                stdio.error(
                    'Cannot resolve a loopback LOG_RESTORE_SOURCE without a persisted primary_tenant mapping.')
                return
            mapped_primary = (primary_info[0][0], primary_info[0][1])
            if mapped_primary not in relation_tenants or mapped_primary[0] not in cluster_configs:
                stdio.error(
                    'The persisted primary_tenant mapping for {}:{} is invalid.'.format(
                        standby_cluster_name, standby_tenant_name))
                return
            candidates = [mapped_primary]

        matches = []
        for relation_deploy_name, relation_tenant_name in candidates:
            relation_cursor = cursors.get(relation_deploy_name)
            if not relation_cursor:
                stdio.verbose("fail to get {}'s cursor".format(relation_deploy_name))
                continue

            res = relation_cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (relation_tenant_name, ), raise_exception=True)
            if not res or not res['ip_list']:
                stdio.verbose("fail to get {}'s ip list".format(relation_deploy_name))
                continue

            relation_cluster_config = cluster_configs.get(relation_deploy_name)
            try:
                primary_ip_list = [
                    ObserverIdentity.externalize_sql_endpoint(relation_cluster_config, endpoint).split('+', 1)[0]
                    if source_is_loopback else endpoint.split('+', 1)[0]
                    for endpoint in primary_ip_list_raw]
            except ObserverIdentityError as e:
                stdio.error(str(e))
                return
            ip_list_value = ObserverIdentity.externalize_ip_list(relation_cluster_config, res['ip_list'])
            ip_list = ip_list_value.split(';')
            if res['TENANT_ID'] == primary_tenant_id and sorted(ip_list) == sorted(primary_ip_list):
                matches.append((relation_deploy_name, relation_tenant_name))
        if len(matches) != 1:
            stdio.error(
                'Expected exactly one primary tenant matching the live LOG_RESTORE_SOURCE, found {}.'.format(
                    len(matches)))
            return
        return matches[0]

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
    if not res or res.get('TENANT_ID') is None:
        error(f"Tenant {cluster_name}:{tenant_name} is not exist.")
        return
    tenant_id = res['TENANT_ID']
    if res['TENANT_ROLE'] == 'PRIMARY':
        error(f'Tenant role {cluster_name}:{tenant_name} is PRIMARY. Unable to perform the current operation.')
        return

    sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s'
    res = cursor.fetchone(sql, (tenant_id, ))
    if not res or res.get('TYPE') is None:
        error(f"{cluster_name}:{tenant_name} log recovery source does not exist. Unable to perform the current operation.")
        return
    current_source_type = res['TYPE']
    plugin_context.set_variable("source_type", current_source_type)

    log_source_type = None
    if kwargs.get('option_mode') == 'log_source':
        primary = get_primary_tenant(cursor, cluster_name, tenant_name, current_source_type)
        if not primary:
            error('Failed to resolve the primary tenant safely.')
            return
        primary_deploy, primary_tenant = primary
        primary_cursor = cursors.get(primary_deploy)
        if not primary_cursor:
            error('Primary deploy {} is not connected.'.format(primary_deploy))
            return
        plugin_context.set_variable("primary_cursor", primary_cursor)
        primary_res = primary_cursor.fetchone('select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (primary_tenant, ), raise_exception=False)
        if not primary_res or primary_res.get('TENANT_ID') is None:
            error('Failed to query primary tenant {}:{}.'.format(primary_deploy, primary_tenant))
            return
        plugin_context.set_variable("primary_tenant_id", primary_res['TENANT_ID'])
        plugin_context.set_variable("primary_tenant", primary_tenant)
        log_source_type = get_option(options, 'type')
    if current_source_type == log_source_type:
        error("Current and target log recovery sources are identical.")
        return

    if kwargs.get('option_mode') == 'switchover_tenant':
        if current_source_type == LOCATION_MODE:
            sql = 'SELECT SYNC_STATUS FROM oceanbase.v$ob_ls_log_restore_status WHERE TENANT_ID=%s'
            res = cursor.fetchone(sql, (tenant_id, ))
            if not res or res.get('SYNC_STATUS') is None:
                error(f"select {cluster_name}:{tenant_name} sync_status is failed")
                return
            sync_status = res['SYNC_STATUS']
            if sync_status != 'NORMAL':
                if sync_status == 'RESTORE SUSPEND':
                    error(err.EC_OBSERVER_LOG_RECOVER.format(cluster_name=cluster_name, tenant_name=tenant_name))
                    return
                
                error(f"The {cluster_name}:{tenant_name} log stream {sync_status} status is unexpected")
                return
            primary = get_primary_tenant(
                cursor, cluster_name, tenant_name, current_source_type)
        else:
            primary = get_primary_tenant(
                cursor, cluster_name, tenant_name, current_source_type)
        if not primary:
            error(f"get {cluster_name}:{tenant_name} primary tenant is failed")
            return
        primary_deploy, primary_tenant = primary
        if current_source_type != LOCATION_MODE:
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
                if not res or res.get('TYPE') is None:
                    stdio.verbose('Select {} log restore source is failed.'.format(relation_deploy_name))
                    continue
                relation_primary = get_primary_tenant(
                    cursor, relation_deploy_name, relation_tenant_name, res['TYPE'])
                if not relation_primary:
                    error(
                        'Failed to resolve primary tenant for {}:{}.'.format(
                            relation_deploy_name, relation_tenant_name))
                    return
                relation_primary_cluster, relation_primary_tenant = relation_primary

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
                        if not primary_cursor:
                            error('Primary deploy {} is not connected.'.format(primary_deploy))
                            return
                        primary_res = primary_cursor.fetchone(
                            'select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s',
                            (primary_tenant, ), raise_exception=False)
                        if not primary_res or primary_res.get('TENANT_ID') is None:
                            error('Failed to query primary tenant {}:{}.'.format(
                                primary_deploy, primary_tenant))
                            return
                        plugin_context.set_variable("check_tenant_id", primary_res['TENANT_ID'])
                        plugin_context.set_variable("check_uri", True)
                        plugin_context.set_variable("check_tenant_cursor", primary_cursor)
                        plugin_context.set_variable('check_tenant', primary_tenant)
                        break
        primary_cursor = cursors.get(primary_deploy)
        if not primary_cursor:
            error('Primary deploy {} is not connected.'.format(primary_deploy))
            return
        primary_res = primary_cursor.fetchone(
            'select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s',
            (primary_tenant,), raise_exception=False)
        if not primary_res or primary_res.get('TENANT_ID') is None:
            error('Failed to query primary tenant {}:{}.'.format(primary_deploy, primary_tenant))
            return
        plugin_context.set_variable("primary_tenant_id", primary_res['TENANT_ID'])
        plugin_context.set_variable("primary_tenant_cursor", primary_cursor)
        plugin_context.set_variable('primary_tenant', primary_tenant)


    stdio.stop_loading("succeed")
    return plugin_context.return_true()
