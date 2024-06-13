# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
import time

from tool import FileUtil


def exec_sql_in_tenant(cursor, tenant, mode='mysql', user='', password='', print_exception=True, retries=20, args=[]):
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'

    query_sql = "select a.SVR_IP,c.SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
    tenant_server_ports = cursor.fetchall(query_sql, (tenant,), raise_exception=False, exc_level='verbose')
    tenant_cursor = []

    for tenant_server_port in tenant_server_ports:
        tenant_ip = tenant_server_port['SVR_IP']
        tenant_port = tenant_server_port['SQL_PORT']
        cursor_tenant = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip,
                                          port=tenant_port, print_exception=print_exception)
        if cursor_tenant:
            tenant_cursor.append(cursor_tenant)
            return tenant_cursor
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(cursor, tenant, mode, user, password, print_exception=print_exception,
                                  retries=retries - 1, args=args)


def scenario_check(scenario):
    if scenario not in ['express_oltp', 'complex_oltp', 'olap', 'htap', 'kv']:
        return False
    return True


def tenant_check(tenant):
    if tenant == 'sys':
        return False
    return True


def tenant_optimize(plugin_context, tenant_name='test', tenant_cursor=None, scenario=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    repositories = plugin_context.repositories

    if tenant_name:
        check_result = tenant_check(tenant_name)
        if not check_result:
            stdio.error('Sys tenant is not supported, please use ordinary tenants')
            return plugin_context.return_false()

    create_tenant = plugin_context.get_return('create_tenant')
    if create_tenant:
        tenant_cursor = create_tenant.get_return('tenant_cursor') if not tenant_cursor else tenant_cursor

    if not tenant_cursor:
        cursor = plugin_context.get_return('connect').get_return('cursor')
        sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = '%s'" % tenant_name
        try:
            tenant = cursor.fetchone(sql, raise_exception=True)
        except Exception as e:
            stdio.exception('Select tenant error, error info:{}'.format(e))
            return
        if not tenant:
            stdio.error('No such Tenant %s' % tenant_name)
            return plugin_context.return_false()
        tenant_cursor = exec_sql_in_tenant(cursor, tenant_name)

    def _optimize(json_files):
        for file in json_files:
            if os.path.exists(file):
                with FileUtil.open(file, 'rb') as f:
                    data = json.load(f)
                    for _ in data:
                        if _['scenario'] == scenario:
                            if 'variables' in _:
                                for tenant_system_variable in _['variables']['tenant']:
                                    sql = f"SET GLOBAL {tenant_system_variable['name']} = {tenant_system_variable['value']};"
                                    for cursor in tenant_cursor:
                                        cursor.execute(sql)
                            if 'parameters' in _:
                                for tenant_default_parameter in _['parameters']['tenant']:
                                    sql = f"ALTER SYSTEM SET {tenant_default_parameter['name']} = '{tenant_default_parameter['value']}';"
                                    for cursor in tenant_cursor:
                                        cursor.execute(sql)
        return True

    if not tenant_cursor:
        stdio.error('tenant cursor is None')
        return plugin_context.return_false()

    path = ''
    for repository in repositories:
        if repository.name == cluster_config.name:
            path = repository.repository_dir
            break

    global_config = cluster_config.get_global_conf_with_default()
    if scenario:
        check_result = scenario_check(scenario)
        if not check_result:
            stdio.error('This scenario is not supported: %s.' % scenario)
            return plugin_context.return_false()
    else:
        stdio.verbose("Tenant optimization scenario not specified, use the cluster scenario: %s." % global_config['scenario'])
        scenario = global_config['scenario']
            
    system_variable_json = f'{path}/etc/default_system_variable.json'
    default_parameters_json = f'{path}/etc/default_parameter.json'
    stdio.start_loading(f'optimize tenant with scenario: {scenario}')
    if _optimize([system_variable_json, default_parameters_json]):
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
