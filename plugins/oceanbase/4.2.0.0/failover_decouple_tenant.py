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
import time
from collections import defaultdict

tenant_cursor_cache = defaultdict(dict)


def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', raise_exception=False, retries=20):
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
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, print_exception=raise_exception)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        retries -= 1
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, raise_exception=raise_exception, retries=retries)
    return tenant_cursor.execute(sql, raise_exception=False, exc_level='verbose') if tenant_cursor else False


def verify_password(cursor, tenant_name, stdio, key='', password='', user='root', mode='mysql'):
    if exec_sql_in_tenant('select 1', cursor, tenant_name, mode, user=user, password=password, raise_exception=False, retries=2):
        return True
    stdio.error("Authentication failed, no valid password for {}:{}. please retry with '--{}=xxxxxx' option.".format(tenant_name, user, key))
    return False


def failover_decouple_tenant(plugin_context, cursors={}, *args, **kwargs):
    def error(msg='', *arg, **kwargs):
        msg and stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('fail')

    stdio = plugin_context.stdio
    deploy_name = plugin_context.cluster_config.deploy_name
    options = plugin_context.options
    cmds = plugin_context.cmds
    option_type = cmds[2]
    tenant_name = getattr(options, 'tenant_name', '')
    standby_cursor = cursors.get(deploy_name)
    # do inner check
    stdio.start_loading('Inner check')
    standby_tenant_password = getattr(plugin_context.options, 'tenant_root_password') if getattr(plugin_context.options, 'tenant_root_password') else ''
    if not verify_password(standby_cursor, tenant_name, stdio, key='tenant-root-password', password=standby_tenant_password):
        stdio.stop_loading('failed')
        return
    try:
        sql = "ALTER SYSTEM ACTIVATE STANDBY VERIFY"
        exec_sql_in_tenant(sql, standby_cursor, tenant_name, mode='mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=2)
    except Exception as e:
        error("Standby tenant {}:{} do {} verify failed:{}".format(deploy_name, tenant_name, option_type, e))
        return
    stdio.stop_loading('succeed')

    # do failover/decouple
    stdio.start_loading('Do {}'.format(option_type))
    try:
        sql = 'ALTER SYSTEM SET LOG_RESTORE_SOURCE = ""'
        exec_sql_in_tenant(sql, standby_cursor, tenant_name, mode='mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=2)
    except Exception as e:
        error("Standby tenant {}:{} do set log restore source failed:{}".format(deploy_name, tenant_name, e))
        return
    try:
        sql = "ALTER SYSTEM ACTIVATE STANDBY"
        exec_sql_in_tenant(sql, standby_cursor, tenant_name, mode='mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=2)
    except Exception as e:
        retry_message = 'After resolving the issue, you can retry by manually executing SQL:\'{}\' with the root user in the tenant {}:{}.'.format(sql, deploy_name, tenant_name)
        error("Do {} on tenant{}:{} failed. error message info:{}. \n {}".format(option_type, deploy_name, tenant_name, e, retry_message))
        return
    plugin_context.set_variable('option_type', option_type)
    stdio.stop_loading('succeed')
    stdio.print('You can use the command "obd cluster tenant show {} -g" to view the relationship between the primary and standby tenants.'.format(deploy_name))
    plugin_context.return_true()