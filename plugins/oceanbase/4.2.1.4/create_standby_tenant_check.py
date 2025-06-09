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

from _stdio import FormatText
from tool import get_option
import _errno as err
from const import LOCATION_MODE, SERVICE_MODE

def create_standby_tenant_check(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    def error(msg='', *arg, **kwargs):
        stdio.stop_loading('failed')
        stdio.error(msg, *arg, **kwargs)

    standby_deploy_name = plugin_context.cluster_config.deploy_name
    current_cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    options = plugin_context.options
    cmds = plugin_context.cmds
    primary_deploy_name = cmds[1]
    primary_tenant = cmds[2]
    primary_cursor = cursors.get(primary_deploy_name)
    stdio.start_loading('Check primary tenant')
    if primary_tenant.lower() == 'sys':
        error('Primary tenant can not be sys.')
        return

    mode = get_option(options, 'mode', 'mysql').lower()
    if not mode in ['mysql', 'oracle']:
        error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
        return

    primary_cluster_config = cluster_configs.get(primary_deploy_name)
    if not primary_cluster_config:
        error('No such deploy: %s.' % primary_deploy_name)
        return False

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
    
    if get_option(options, 'type') == SERVICE_MODE:
        # check primary cluster have full log stream
        sql = '(select LS_ID from oceanbase.DBA_OB_LS_HISTORY) minus (select LS_ID from oceanbase.DBA_OB_LS)'
        try:
            res = primary_cursor.fetchone(sql, raise_exception=True)
        except Exception as e:
            error('Check primary cluster have full log stream failed. error:{}'.format(e))
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
            error(err.EC_OBSERVER_LOG_INCOMPLETE.format(primary_tenant=primary_tenant))
            return

        sql = 'select TENANT_ROLE from oceanbase.DBA_OB_TENANTS where TENANT_ID=%s' % primary_tenant_info['tenant_id']
        res = primary_cursor.fetchone(sql)
        if not res or res['TENANT_ROLE'] is None:
            error('Find primary tenant role is failed')
            return
        if res['TENANT_ROLE'] == "STANDBY":
            sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % primary_tenant_info['tenant_id']
            res = primary_cursor.fetchone(sql)
            if not res or res['TYPE'] is None:
                error(f'Find {primary_deploy_name} log recovery source is failed')
                return
            if res['TYPE'] == LOCATION_MODE:
                error(err.EC_OBSERVER_LOCATION_CREATE_STANDBY.format(primary_tenant=primary_tenant))
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
    plugin_context.set_variable('error', error)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()