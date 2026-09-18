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
from _rpm import Version
from const import LOCATION_MODE
from _deploy import ObserverIdentity, ObserverIdentityError


def switchover_tenant_pre(plugin_context, repository, cursors={}, cluster_configs={}, relation_tenants={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    options = plugin_context.options
    standby_tenant = getattr(options, 'tenant_name', '')
    standby_cursor = cursors.get(standby_deploy_name)
    if not standby_cursor:
        stdio.error('Failed to connect standby deploy: {}.'.format(standby_deploy_name))
        return False
    sql = "select TENANT_ROLE from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    tenant_role_res = standby_cursor.fetchone(sql, (standby_tenant, ), raise_exception=True)
    if not tenant_role_res:
        stdio.error("{}:{} not exists".format(standby_deploy_name, standby_tenant))
        return
    if tenant_role_res['TENANT_ROLE'] != 'STANDBY':
        stdio.error("{}:{} is not standby tenant.".format(standby_deploy_name, standby_tenant))
        return

    res = standby_cursor.fetchone('select a.VALUE as `VALUE` from oceanbase.cdb_ob_log_restore_source as a, oceanbase.DBA_OB_TENANTS as b where a.TENANT_ID=b.TENANT_ID and b.TENANT_NAME = %s ', (standby_tenant, ), raise_exception=False)
    if not res:
        stdio.error("Query tenant {}:{}'s primary tenant info fail, place confirm current tenant is have the primary tenant.".format(standby_deploy_name, standby_tenant))
        return

    primary = {}
    cluster_config = cluster_configs.get(standby_deploy_name)
    if not cluster_config:
        stdio.error("Get {} cluster config is failed.".format(standby_deploy_name))
        return
    primary_dict = cluster_config.get_component_attr('primary_tenant')
    primary_info = primary_dict.get(standby_tenant, []) if primary_dict else []
    mapped_primary = (primary_info[0][0], primary_info[0][1]) if primary_info else None

    if kwargs.get('source_type', None) == LOCATION_MODE:
        if not mapped_primary or mapped_primary not in relation_tenants or \
                mapped_primary[0] not in cluster_configs:
            stdio.error(
                'Tenant {} cannot find valid primary tenant information'.format(standby_tenant))
            return
        primary['primary_deploy_name'] = mapped_primary[0]
        primary['primary_tenant'] = mapped_primary[1]
    else:
        primary_info_dict = {}
        for item in res['VALUE'].split(','):
            key, separator, value = item.partition('=')
            if separator:
                primary_info_dict[key] = value
        primary_ip_list_value = primary_info_dict.get('IP_LIST')
        primary_tenant_id_value = primary_info_dict.get('TENANT_ID')
        if not primary_ip_list_value or not primary_tenant_id_value:
            stdio.error('Invalid SERVICE LOG_RESTORE_SOURCE for tenant {}:{}.'.format(
                standby_deploy_name, standby_tenant))
            return
        primary_ip_list_raw = primary_ip_list_value.split(';')
        primary_tenant_id = int(primary_tenant_id_value)
        source_is_loopback = any(
            endpoint.split('+', 1)[0].rpartition(':')[0] == '127.0.0.1'
            for endpoint in primary_ip_list_raw)

        if source_is_loopback:
            if not mapped_primary or mapped_primary not in relation_tenants or \
                    mapped_primary[0] not in cluster_configs:
                stdio.error(
                    'Cannot resolve a loopback LOG_RESTORE_SOURCE without a valid persisted primary_tenant mapping.')
                return
            primary_deploy_name, primary_tenant_name = mapped_primary
            primary_cluster_config = cluster_configs.get(primary_deploy_name)
            try:
                primary_ip_list = [
                    ObserverIdentity.externalize_sql_endpoint(primary_cluster_config, endpoint).split('+', 1)[0]
                    for endpoint in primary_ip_list_raw]
            except ObserverIdentityError as e:
                stdio.error(str(e))
                return
            primary_cursor = cursors.get(primary_deploy_name)
            if not primary_cursor:
                stdio.error('Primary deploy: {} connect check fail.'.format(primary_deploy_name))
                return
            candidate = primary_cursor.fetchone(
                'select TENANT_ID, group_concat(host separator ";") as ip_list from '
                '(select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from '
                'oceanbase.cdb_ob_access_point where tenant_name=%s)',
                (primary_tenant_name, ), raise_exception=True)
            candidate_ip_list = ObserverIdentity.externalize_ip_list(
                primary_cluster_config, candidate['ip_list']).split(';') if candidate and candidate['ip_list'] else []
            if candidate and candidate['TENANT_ID'] == primary_tenant_id and \
                    sorted(candidate_ip_list) == sorted(primary_ip_list):
                primary['primary_deploy_name'] = primary_deploy_name
                primary['primary_tenant'] = primary_tenant_name
            else:
                stdio.error(
                    'The persisted primary_tenant mapping does not match the live loopback LOG_RESTORE_SOURCE.')
                return
        else:
            primary_ip_list = sorted(endpoint.split('+', 1)[0] for endpoint in primary_ip_list_raw)
            matches = []
            for relation_deploy_name, relation_tenant_name in relation_tenants:
                relation_cursor = cursors.get(relation_deploy_name)
                if not relation_cursor:
                    stdio.verbose("fail to get {}'s cursor".format(relation_deploy_name))
                    continue
                candidate = relation_cursor.fetchone(
                    'select TENANT_ID, group_concat(host separator ";") as ip_list from '
                    '(select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from '
                    'oceanbase.cdb_ob_access_point where tenant_name=%s)',
                    (relation_tenant_name, ), raise_exception=True)
                if not candidate or not candidate['ip_list']:
                    stdio.verbose("fail to get {}'s ip list".format(relation_deploy_name))
                    continue
                relation_cluster_config = cluster_configs.get(relation_deploy_name)
                candidate_ip_list = ObserverIdentity.externalize_ip_list(
                    relation_cluster_config, candidate['ip_list']).split(';')
                if candidate['TENANT_ID'] == primary_tenant_id and sorted(candidate_ip_list) == primary_ip_list:
                    matches.append((relation_deploy_name, relation_tenant_name))
            if len(matches) != 1:
                stdio.error(
                    'Expected exactly one primary tenant matching the live LOG_RESTORE_SOURCE, found {}.'.format(
                        len(matches)))
                return
            primary['primary_deploy_name'] = matches[0][0]
            primary['primary_tenant'] = matches[0][1]

    if not primary:
        stdio.error('Tenant: {}:{} not found primary tenant'.format(standby_deploy_name, standby_tenant))
        return False
    cluster_configs[standby_deploy_name] = plugin_context.cluster_config

    primary_deploy_name = primary['primary_deploy_name']
    primary_tenant = primary['primary_tenant']
    primary_cursor = cursors.get(primary_deploy_name)
    if not primary_cursor:
        stdio.error('Primary deploy: {} connect check fail.'.format(primary_deploy_name))
        return False
    version_info = primary_cursor.fetchone('select version() as version')
    if not version_info:
        stdio.error('Get primary tenant {}:{} version fail'.format(primary_deploy_name, primary_tenant))
        return False
    primary_version = version_info['version'].lower().split('-v')[-1]
    if repository.version != Version(primary_version):
        stdio.error('Version not match. standby version: {}, primary version: {}.'.format(repository.version, primary_version))
        return False

    plugin_context.set_variable('primary_info', primary)
    return plugin_context.return_true(primary_info=primary)
