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

from const import LOCATION_MODE

def get_ip_list(cursor, deploy_name, tenant, stdio):
    if not cursor:
        stdio.verbose("Connect to {} failed.".format(deploy_name))
        return
    res = cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (tenant, ), raise_exception=True)
    if not res:
        stdio.stop_loading('stop_loading', 'fail')
        return
    if not res['ip_list']:
        stdio.verbose('tenant:{}:{} is not exist.'.format(deploy_name, tenant))
        return
    ip_list = res['ip_list'].split(';')
    if not ip_list:
        stdio.error('Query ip list error for tenant:{}:{}.'.format(deploy_name, tenant))
        return False
    ip_list.sort()
    return ip_list


def get_standbys(plugin_context, primary_tenant='', relation_tenants=[], all_tenant_names=[], exclude_tenant=[], cursors={}, skip_no_primary_cursor=False, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    cluster_version = plugin_context.cluster_config.version
    cluster_configs = kwargs.get('cluster_configs')
    primary_deploy_name = kwargs.get('primary_deploy_name')
    primary_deploy_name = primary_deploy_name if primary_deploy_name else plugin_context.cluster_config.deploy_name
    primary_tenant = primary_tenant if primary_tenant else getattr(options, 'tenant_name', '')
    stdio.start_loading('Get standbys info')
    if skip_no_primary_cursor and (not cursors or not cursors.get(primary_deploy_name)):
        stdio.verbose('Connect to {} failed. skip get standby'.format(primary_deploy_name))
        plugin_context.set_variable('standby_tenants', [])
        plugin_context.set_variable('no_primary_cursor', True)
        stdio.stop_loading('succeed')
        return plugin_context.return_true(standby_tenants=[])

    if not cursors:
        stdio.error('Connect to OceanBase failed.')
        stdio.stop_loading('fail')
        return

    standby_tenants = []
    # find primary tenant`s ip list
    primary_cursor = cursors.get(primary_deploy_name)
    if not primary_cursor:
        stdio.error("Connect to {} failed".format(primary_deploy_name))
        stdio.stop_loading('fail')
        return
    
    all_tenant_names = [primary_tenant] if primary_tenant else all_tenant_names
    for tenant_name in all_tenant_names:
        ip_list = get_ip_list(primary_cursor, primary_deploy_name, tenant_name, stdio)
        res = primary_cursor.fetchone('select TENANT_ID from oceanbase.DBA_OB_TENANTS where tenant_name=%s', (tenant_name, ), raise_exception=False)
        if not res:
            stdio.verbose('tenant:{}:{} is not exist.'.format(primary_deploy_name, tenant_name)) 
            continue
        tenant_id = res['TENANT_ID']
        stdio.verbose("find primary, primary tenant {}:{}'s ip list:{}, relation_tenants:{}, exclude_tenant:{}".format(primary_deploy_name, tenant_name, ip_list, relation_tenants, exclude_tenant))
        for relation_tenant in relation_tenants:
            relation_deploy_name = relation_tenant[0]
            relation_tenant_name = relation_tenant[1]
            if [relation_deploy_name, relation_tenant_name] == exclude_tenant:
                continue
            if primary_deploy_name == relation_deploy_name and tenant_name == relation_tenant_name:
                continue
            cursor = cursors.get(relation_deploy_name)
            if not cursor:
                stdio.verbose("Connect to {} failed.".format(relation_deploy_name))
                continue
            res = cursor.fetchone('select TENANT_ROLE,TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (relation_tenant_name, ), raise_exception=False)
            if not res:
                continue
            if res['TENANT_ROLE'] == 'PRIMARY':
                continue

            if cluster_version >= '4.2.1.9':
                tenant_cluster_info = cluster_configs.get(relation_deploy_name)
                if not tenant_cluster_info:
                    stdio.verbose("Get {} cluster info is failed.".format(relation_deploy_name))
                    continue

                sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % res['TENANT_ID']
                res = cursor.fetchone(sql, raise_exception=False)
                if not res:
                    stdio.verbose('Select {} log restore source is failed.'.format(relation_deploy_name))
                    continue

                primary_dict = tenant_cluster_info.get_component_attr('primary_tenant')
                primary_info = []
                if primary_dict:
                    primary_info = primary_dict.get(relation_tenant_name, [])
                    if primary_info:
                        primary_match = (primary_info[0][0] == primary_deploy_name and primary_info[0][1] == primary_tenant)
                        primary_match_empty_tenant = (primary_tenant == '' and primary_info[0][0] == primary_deploy_name)
                        if primary_match or primary_match_empty_tenant:
                            sql = 'select ob_version() as version'
                            res = cursor.fetchone(sql, raise_exception=False)
                            standby_tenants.append([relation_deploy_name, relation_tenant_name, res['version']])
                            continue
                if res['TYPE'] == LOCATION_MODE or primary_info:
                    continue

            res = cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s', (relation_tenant_name, ), raise_exception=False)
            if res is False:
                stdio.stop_loading('stop_loading', 'fail')
                return
            if not res:
                stdio.verbose("tenant:{}:{}`primary tenant is not exist".format(relation_deploy_name, relation_tenant_name))
                continue

            primary_info_dict = {}
            primary_info_arr = res['VALUE'].split(',')
            for primary_info in primary_info_arr:
                kv = primary_info.split('=')
                primary_info_dict[kv[0]] = kv[1]
            primary_ip_list = primary_info_dict.get('IP_LIST').split(';')
            primary_ip_list.sort()
            primary_tenant_id = primary_info_dict.get('TENANT_ID')
            if primary_ip_list == ip_list and tenant_id == int(primary_tenant_id):
                sql = 'select ob_version() as version'
                res = cursor.fetchone(sql, raise_exception=False)
                standby_tenants.append([relation_deploy_name, relation_tenant_name, res['version']])
                if cluster_version >= '4.2.1.9':
                    primary_dict = tenant_cluster_info.get_component_attr('primary_tenant')
                    if primary_dict:
                        primary_dict[relation_tenant_name] = [[primary_deploy_name, primary_tenant]]
                        tenant_cluster_info.update_component_attr('primary_tenant', primary_dict, save=True)
                    else:
                        primary_dict = {relation_tenant_name: [[primary_deploy_name, primary_tenant]]}
                        tenant_cluster_info.update_component_attr('primary_tenant', primary_dict, save=True)
    plugin_context.set_variable('standby_tenants', standby_tenants)
    stdio.stop_loading('succeed')
    return plugin_context.return_true(standby_tenants=standby_tenants)