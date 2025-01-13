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
    primary_info_dict = {}
    primary = {}
    primary_info_arr = res['VALUE'].split(',')
    for primary_info in primary_info_arr:
        kv = primary_info.split('=')
        primary_info_dict[kv[0]] = kv[1]
    primary_ip_list = primary_info_dict.get('IP_LIST').split(';')
    primary_ip_list.sort()
    primary_tenant_id = int(primary_info_dict['TENANT_ID']) if primary_info_dict else None
    # find primary tenant
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
            primary['primary_deploy_name'] = relation_deploy_name
            primary['primary_tenant'] = relation_tenant_name
            break

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
