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

from tool import ConfigUtil
from _stdio import FormatText

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
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, print_exception=print_exception)
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


def create_standby_tenant_pre(plugin_context, primary_deploy_name, primary_tenant, cursors={}, cluster_configs={}, *args, **kwargs):
    def error(msg='', *arg, **kwargs):
        msg and stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('fail')

    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value

    options = plugin_context.options
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    current_cluster_config = plugin_context.cluster_config
    plugin_context.cluster_config = current_cluster_config
    primary_cursor = cursors.get(primary_deploy_name)
    stdio.start_loading('Check primary tenant')
    if primary_tenant.lower() == 'sys':
        error('Primary tenant can not be sys.')
        return

    mode = get_option('mode', 'mysql').lower()
    if not mode in ['mysql', 'oracle']:
        error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
        return

    primary_cluster_config = cluster_configs.get(primary_deploy_name)
    if not primary_cluster_config:
        stdio.error('No such deploy: %s.' % primary_deploy_name)
        return False

    root_password = get_option('tenant_root_password', '')
    standbyro_password_input = get_option('standbyro_password', None)
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

    # check primary tenant is exist
    sql = 'select tenant_id,compatibility_mode,primary_zone from oceanbase.__all_tenant where tenant_name=%s'
    primary_tenant_info = primary_cursor.fetchone(sql, (primary_tenant, ))
    if not primary_tenant_info:
        error('Primary tenant {}:{} is not exist.'.format(primary_deploy_name, primary_tenant))
        return

    # check compatibility mode
    sql = 'SELECT compatibility_mode FROM oceanbase.DBA_OB_TENANTS where tenant_name=%s'
    res_compatibility = primary_cursor.fetchone(sql, (primary_tenant, ))
    if not res_compatibility:
        error('Query {}:{} compatibility_mode fail.'.format(primary_deploy_name, primary_tenant))
        return
    if res_compatibility['compatibility_mode'].lower() != 'mysql':
        error('Primary tenant {}:{} compatibility_mode is not mysql. only support mysql now!'.format(primary_deploy_name, primary_tenant))
        return

    # check primary tenant have full log stream
    sql = '(select LS_ID from oceanbase.DBA_OB_LS_HISTORY) minus (select LS_ID from oceanbase.DBA_OB_LS)'
    try:
        res = primary_cursor.fetchone(sql, raise_exception=True)
    except Exception as e:
        error('Check primary tenant have full log stream failed. error:{}'.format(e))
        return
    if res:
        error('Primary cluster have not full log stream, not support create standby cluster.')
        return

    # check primary tenant have full log
    sql = 'select MAX(BEGIN_LSN) as max_begin_lsn from oceanbase.GV$OB_LOG_STAT as a WHERE a.tenant_id =%s'
    res = primary_cursor.fetchone(sql, (primary_tenant_info['tenant_id'], ))
    if not res or res['max_begin_lsn'] is None:
        error('Check primary tenant have full log failed.')
        stdio.print(FormatText.success('Please try again in a moment.'))
        return
    if res['max_begin_lsn'] > 0:
        error('Primary cluster have not full log, not support create standby cluster.')
        return

    sql = '''
            select time_to_usec(t1.modify_time) as update_time, t1.resource_pool_id, t1.name, t1.unit_count, t1.unit_config_id, t1.zone_list, t1.tenant_id,
               t1.replica_type,t2.name as unit_config_name, t2.max_cpu, t2.min_cpu, t2.memory_size, t2.log_disk_size, t2.max_iops, t2.min_iops, t2.iops_weight
            from oceanbase.dba_ob_resource_pools as t1 join oceanbase.dba_ob_unit_configs as t2  on t1.unit_config_id = t2.unit_config_id and t1.tenant_id=%s
          '''
    res = primary_cursor.fetchone(sql, (primary_tenant_info['tenant_id'], ))
    if res is False:
        error('Check primary tenant info failed.')
        return
    res['max_cpu'] = int(res['max_cpu'])
    res['min_cpu'] = int(res['min_cpu'])
    res['unit_num'] = int(res['unit_count'])
    res['primary_deploy_name'] = primary_deploy_name
    res['primary_tenant'] = primary_tenant
    plugin_context.set_variable('primary_tenant_info', res)
    cluster_configs[standby_deploy_name] = current_cluster_config
    plugin_context.set_variable('cluster_configs', cluster_configs)

    # create standbyro in primary tenant
    # try to connect to tenant with standbyro if the user has entered a password or there is a password in the inner_config
    if (standbyro_password_input is None and not standbyro_password_inner) or not exec_sql_in_tenant('select 1', primary_cursor, primary_tenant, mode, user='standbyro', password=standbyro_password, print_exception=False, retries=2, exec_type='fetchone'):
        # can not connect to tenant with standbyro user, try to connect to tenant with root user
        if exec_sql_in_tenant('select 1', primary_cursor, primary_tenant, mode, password=root_password, print_exception=False, retries=2, exec_type='fetchone'):
            # if standbyro exists ?
            sql = "select * from oceanbase.__all_user where user_name = 'standbyro'"
            if exec_sql_in_tenant(sql, primary_cursor, primary_tenant, mode, password=root_password, print_exception=False, retries=1, exec_type='fetchone'):
                error("Authentication failed because the standbyro user already exists but the password is incorrect. Please re-create the tenant with ' --standbyro-password=xxxxxx'")
                return
            # create standbyro
            sql = "CREATE USER standbyro IDENTIFIED BY %s"
            if not exec_sql_in_tenant(sql, primary_cursor, primary_tenant, mode, args=[standbyro_password], password=root_password, retries=1):
                error('Create standbyro user failed')
                return
        else:
            # can not connect to tenant with root user,need user supply password
            error("Authentication failed because the root_password is invalid for the primary tenant. Please re-create the tenant with '--tenant-root-password=xxxxxx'")
            return

    # GRANT oceanbase to standbyro
    if not exec_sql_in_tenant('show databases like "oceanbase"', primary_cursor, primary_tenant, mode, user='standbyro', password=standbyro_password, print_exception=False, retries=1, exec_type='fetchone') and \
          not exec_sql_in_tenant("GRANT SELECT ON oceanbase.* TO standbyro;", primary_cursor, primary_tenant, mode, password=root_password, retries=3):
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
