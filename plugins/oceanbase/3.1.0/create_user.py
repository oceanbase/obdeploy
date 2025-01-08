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


from __future__ import absolute_import, division, print_function

import time

import const

from collections import defaultdict

tenant_cursor = None

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
        query_sql = "select a.svr_ip,c.inner_port from oceanbase.__all_unit as a, oceanbase.__all_tenant as b, oceanbase.__all_server as c, oceanbase.__all_resource_pool as d where a.resource_pool_id=d.resource_pool_id and a.svr_ip=c.svr_ip and a.svr_port=c.svr_port and d.tenant_id=b.tenant_id and tenant_name=%s"
        cursor = cursor.usable_cursor
        tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
        for tenant_server_port in tenant_server_ports:
            tenant_ip = tenant_server_port['svr_ip']
            tenant_port = tenant_server_port['inner_port']
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password if retries % 2 or not len(args) > 0 else args[0], ip=tenant_ip, port=tenant_port, print_exception=False)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, print_exception=print_exception, retries=retries-1, args=args, stdio=stdio)
    return tenant_cursor.execute(sql, args=args, raise_exception=False, exc_level='verbose', stdio=stdio) if tenant_cursor else False


def create_user(plugin_context, create_tenant_options=[], cursor=None, scale_out_component='',  *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    password = cluster_config.get_global_conf().get('root_password', '')
    error = plugin_context.get_variable('error')
    cursor = plugin_context.get_return('connect', spacename=cluster_config.name).get_return('cursor') if not cursor else cursor
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    if scale_out_component in const.COMPS_OCP_CE_AND_EXPRESS:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    if not multi_options:
        multi_options = plugin_context.get_variable('create_tenant_options')
    for options in multi_options:
        global tenant_cursor
        tenant_cursor = None
        name = getattr(options, 'tenant_name', 'sys')
        mode = getattr(options, 'mode', 'mysql')
        database = getattr(options, 'database', '')
        db_username = getattr(options, 'db_username', '')
        db_password = getattr(options, 'db_password', '')
        create_if_not_exists = getattr(options, 'create_if_not_exists', False)
        if database:
            sql = 'create database {}'.format(database)
            if not exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, mode=mode, password=password, stdio=stdio) and not create_if_not_exists:
                stdio.error('failed to create database {}'.format(database))
                return plugin_context.return_false()

        if db_username:
            create_sql, grant_sql = "", ""
            if mode == "mysql":
                create_sql = "create user if not exists '{username}' IDENTIFIED BY %s;".format(username=db_username)
                grant_sql = "grant all on *.* to '{username}' WITH GRANT OPTION;".format(username=db_username)
            else:
                error("Create user in oracle tenant is not supported")
            if not exec_sql_in_tenant(sql=create_sql, cursor=cursor, tenant=name, mode=mode, password=password, args=[db_password], stdio=stdio):
                stdio.error('failed to create user {}'.format(db_username))
                return plugin_context.return_false()
            if not exec_sql_in_tenant(sql=grant_sql, cursor=cursor, tenant=name, mode=mode, password=password, stdio=stdio):
                stdio.error('Failed to grant privileges to user {}'.format(db_username))
                return plugin_context.return_false()
    plugin_context.set_variable('exec_sql_in_tenant', exec_sql_in_tenant)
    return plugin_context.return_true()