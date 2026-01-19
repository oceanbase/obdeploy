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
import const
from collections import defaultdict


tenant_cursor_cache = defaultdict(dict)


def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', print_exception=True, retries=20, args=[], stdio=None):
    global tenant_cursor
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'
    # find tenant ip, port
    tenant_cursor = None
    if cursor in tenant_cursor_cache and tenant in tenant_cursor_cache[cursor] and user in tenant_cursor_cache[cursor][tenant]:
        tenant_cursor = tenant_cursor_cache[cursor][tenant][user]
    else:
        query_sql = "select a.SVR_IP,c.SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
        tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
        for tenant_server_port in tenant_server_ports:
            tenant_ip = tenant_server_port['SVR_IP']
            tenant_port = tenant_server_port['SQL_PORT']
            pwd = password if retries % 2 else ''
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=pwd, ip=tenant_ip, port=tenant_port, mode=mode, print_exception=False)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, print_exception=print_exception, retries=retries - 1, args=args, stdio=stdio)
    if not tenant_cursor:
        return False
    if mode == 'mysql':
        while tenant_cursor.execute('show databases;', exc_level='verbose') is False:
            stdio.verbose('Server is initializing...')
            time.sleep(2)
    try_times = 300
    while try_times:
        rv = tenant_cursor.execute(sql, args=args, raise_exception=False, exc_level='verbose', stdio=stdio)
        if rv is False:
            try_times -= 1
            time.sleep(1)
            continue
        break
    return rv


def create_user(plugin_context, create_tenant_options=[], cursor=None, scale_out_component='',  *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    error = plugin_context.get_variable('error')
    cursor = plugin_context.get_return('connect', spacename=cluster_config.name).get_return('cursor') if not cursor else cursor
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    create_tenant_components = const.COMPS_OCP + [const.COMP_PRAG, 'ocp-express', 'obbinlog-ce', 'obbinlog']
    if scale_out_component in create_tenant_components:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    if not multi_options:
        multi_options = plugin_context.get_variable('create_tenant_options')
    if cursor:
        tenant_cursor_cache[cursor]['sys' if not cursor.tenant else cursor.tenant] = {}
        tenant_cursor_cache[cursor]['sys' if not cursor.tenant else cursor.tenant][cursor.user] = cursor
    for options in multi_options:
        global tenant_cursor
        tenant_cursor = None
        name = getattr(options, 'tenant_name', 'sys')
        mode = getattr(options, 'mode', 'mysql')
        database = getattr(options, 'database', '')
        db_username = getattr(options, 'db_username', '')
        db_password = getattr(options, 'db_password', '')
        root_password = getattr(options, name+'_root_password', "")
        create_if_not_exists = getattr(options, 'create_if_not_exists', False)

        if root_password:
            sql = f"""alter user {'root' if mode== 'mysql' else 'SYS' } IDENTIFIED BY "{root_password}" """;
            stdio.verbose(sql)
            if not exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, mode=mode, stdio=stdio) and not create_if_not_exists:
                stdio.error(f"failed to set {'root' if mode== 'mysql' else 'SYS' }@{name}\'s root_password")
                return plugin_context.return_false()

        if database:
            sql = 'create database if not exists {}'.format(database)
            if not exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, mode=mode, password=root_password if root_password else '', stdio=stdio) and not create_if_not_exists:
                stdio.error('failed to create database {}'.format(database))
                return plugin_context.return_false()

        if db_username:
            if mode == 'oracle':
                stdio.print('Create user in oracle tenant is not supported')
                return plugin_context.return_true()

            create_sql, grant_sql = "", ""
            if mode == "mysql":
                create_sql = "create user if not exists '{username}' IDENTIFIED BY %s;".format(username=db_username)
                grant_sql = "grant all on *.* to '{username}' WITH GRANT OPTION;".format(username=db_username)
            if not exec_sql_in_tenant(sql=create_sql, cursor=cursor, tenant=name, mode=mode, args=[db_password], stdio=stdio):
                stdio.error('failed to create user {}'.format(db_username))
                return plugin_context.return_false()
            if not exec_sql_in_tenant(sql=grant_sql, cursor=cursor, tenant=name, mode=mode, stdio=stdio):
                stdio.error('Failed to grant privileges to user {}'.format(db_username))
                return plugin_context.return_false()
    return plugin_context.return_true()