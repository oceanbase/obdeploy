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

import time
from collections import defaultdict
from tool import ConfigUtil, get_option

tenant_cursor_cache = defaultdict(dict)

def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', args=None, print_exception=True, retries=20, exec_type='exec'):
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
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, mode=mode, print_exception=print_exception)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, args=args, print_exception=print_exception, retries=retries-1, exec_type=exec_type)
    if exec_type == 'exec':
        return tenant_cursor.execute(sql, args=args, raise_exception=False, exc_level='verbose') if tenant_cursor else False
    elif exec_type == 'fetchone':
        return tenant_cursor.fetchone(sql, args=args, raise_exception=False, exc_level='verbose') if tenant_cursor else False
    else:
        return False

def create_standbyro(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')
        
    options = plugin_context.options
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    if kwargs.get('option_mode') == 'log_source':
        primary_deploy_name = plugin_context.get_variable('primary_deploy')
        primary_tenant = plugin_context.get_variable('primary_tenant')
    elif kwargs.get('option_mode') == 'switchover':
        primary_deploy_name = plugin_context.get_variable('switchover_cluster')
        primary_tenant = plugin_context.get_variable('switchover_tenant')
    else:
        primary_deploy_name = cmds[1]
        primary_tenant = cmds[2]
    primary_cursor = cursors.get(primary_deploy_name)
    primary_cluster_config = cluster_configs.get(primary_deploy_name)
    mode = get_option(options, 'mode', 'mysql').lower()

    stdio.start_loading('Create standbyro user')
    root_password = get_option(options, 'tenant_root_password', '')
    standbyro_password_input = get_option(options, 'standbyro_password', None)
    # check standbyro_password
    if standbyro_password_input == '':
        error('Invalid standbyro password. The password cannot be an empty string')
        return
    if standbyro_password_input is not None:
        invalid_char = ["'", '"', '`', ";", " ", ]
        for char in invalid_char:
            if char in standbyro_password_input:
                error('Invalid standbyro password. The password can not contain %s' % invalid_char)
                return

    standbyro_password_inner = None
    if standbyro_password_input is None:
        standbyro_password_inner = primary_cluster_config.get_component_attr('standbyro_password')
        if standbyro_password_inner and standbyro_password_inner.get(primary_tenant, ''):
            standbyro_password = standbyro_password_inner.get(primary_tenant, '')
        else:
            standbyro_password = ConfigUtil.get_random_pwd_by_total_length()
    else:
        standbyro_password = standbyro_password_input

    # create standbyro in primary tenant
    # try to connect to tenant with standbyro if the user has entered a password or there is a password in the inner_config
    if (standbyro_password_input is None and not standbyro_password_inner) or not exec_sql_in_tenant('select 1' if mode == 'mysql' else 'select 1 from DUAL', primary_cursor, primary_tenant, mode, user='standbyro', password=standbyro_password, print_exception=False, retries=2, exec_type='fetchone'):
        # can not connect to tenant with standbyro user, try to connect to tenant with root user
        if exec_sql_in_tenant('select 1' if mode == 'mysql' else 'select 1 from DUAL', primary_cursor, primary_tenant, mode, password=root_password, print_exception=False, retries=2, exec_type='fetchone'):
            # if standbyro exists ?
            sql = "select * from %s.__all_user where user_name = 'standbyro'" % ('oceanbase' if mode == 'mysql' else 'SYS')
            if exec_sql_in_tenant(sql, primary_cursor, primary_tenant, mode, password=root_password, print_exception=False, retries=1, exec_type='fetchone'):
                error("Authentication failed because the standbyro user already exists but the password is incorrect. Please re-create the tenant with ' --standbyro-password=xxxxxx'")
                return
            # create standbyro
            sql = f"""CREATE USER standbyro IDENTIFIED BY "{standbyro_password}" """
            if not exec_sql_in_tenant(sql, primary_cursor, primary_tenant, mode, password=root_password, retries=1):
                error('Create standbyro user failed')
                return
        else:
            # can not connect to tenant with root user,need user supply password
            error("Authentication failed because the root_password is invalid for the primary tenant. Please re-create the tenant with '--tenant-root-password=xxxxxx'")
            return

    # GRANT oceanbase to standbyro
    show_db_sql = 'show databases like "oceanbase"' if mode == 'mysql' else "SELECT username FROM all_users WHERE username = 'SYS'"
    grant_sql = "GRANT SELECT ON %s.* TO standbyro;" % ("oceanbase" if mode == "mysql" else "SYS")
    if not exec_sql_in_tenant(show_db_sql, primary_cursor, primary_tenant, mode, user='standbyro', password=standbyro_password, print_exception=False, retries=1, exec_type='fetchone'):
        error("show database error")
        return
    if not exec_sql_in_tenant(grant_sql, primary_cursor, primary_tenant, mode, password=root_password, retries=3):
        error('Grant standbyro failed')
        return

    standbyro_password_dict = primary_cluster_config.get_component_attr('standbyro_password')
    if standbyro_password_dict:
        standbyro_password_dict[primary_tenant] = standbyro_password
    else:
        standbyro_password_dict = {primary_tenant: standbyro_password}
    if not primary_cluster_config.update_component_attr('standbyro_password', standbyro_password_dict, save=True):
        error('Dump standbyro password failed.')
        return

    plugin_context.set_variable('standbyro_password', standbyro_password)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
