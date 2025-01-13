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

import datetime
from _types import Capacity


def list_tenant(plugin_context, cursor, relation_tenants={}, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(plugin_context.options, key, default)
        if not value:
            value = default
        return value
    deploy_name = plugin_context.deploy_name
    tenant_name = get_option('tenant', '')
    stdio = plugin_context.stdio
    stdio.start_loading('Select tenant')
    tenant_infos = []
    if tenant_name:
        sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    else:
        sql = "select * from oceanbase.DBA_OB_TENANTS"
    tenant_names = cursor.fetchall(sql, (tenant_name, ) if tenant_name else None)
    if not tenant_names:
        stdio.error('{} not exists in {}'.format(tenant_name, deploy_name))
        stdio.stop_loading('fail')
        return

    need_list_standby = False
    standby_tenants = []
    for tenant in tenant_names:
        if tenant_name and tenant['TENANT_NAME'] != tenant_name:
            continue

        select_resource_pools_sql = "select UNIT_CONFIG_ID from oceanbase.DBA_OB_RESOURCE_POOLS where TENANT_ID = %s"
        if tenant['TENANT_TYPE'] == 'META':
            continue
        res = cursor.fetchone(select_resource_pools_sql, (tenant['TENANT_ID'], ))
        if res is False:
            stdio.stop_loading('fail')
            return
        select_unit_configs_sql = "select * from oceanbase.DBA_OB_UNIT_CONFIGS where UNIT_CONFIG_ID = %s"
        res = cursor.fetchone(select_unit_configs_sql, (res['UNIT_CONFIG_ID'], ))
        if res is False:
            stdio.stop_loading('fail')
            return

        if tenant['TENANT_ROLE'] == 'STANDBY':
            query_standby_tenant_sql = "SELECT LS_ID,SYNC_STATUS, ERR_CODE, COMMENT as ERROR_COMMENT,b.VALUE as PRIMARY_TENANT_INFO, (CASE WHEN SYNC_STATUS = 'NORMAL' THEN 5 WHEN SYNC_STATUS = 'RESTORE SUSPEND' THEN 4 WHEN SYNC_STATUS = 'SOURCE HAS A GAP' THEN 1 WHEN SYNC_STATUS = 'STANDBY LOG NOT MATCH' THEN 2 ELSE 3 END) AS SYNC_STATUS_WEIGHT FROM oceanbase.v$ob_ls_log_restore_status as a, oceanbase.cdb_ob_log_restore_source as b where a.tenant_id =%s order by SYNC_STATUS_WEIGHT limit 1"
            res_status = cursor.fetchone(query_standby_tenant_sql, (tenant['TENANT_ID'], ))
            res_status and standby_tenants.append(dict(tenant, **res_status))
            need_list_standby = True
        elif (deploy_name, tenant['TENANT_NAME']) in relation_tenants:
            need_list_standby = True

        tenant_infos.append(dict(tenant, **res))
    stdio.stop_loading('succeed')
    if tenant_infos:
        stdio.print_list(tenant_infos, ['tenant_name', 'tenant_type', 'compatibility_mode', 'primary_zone', 'max_cpu',
                                        'min_cpu', 'memory_size', 'max_iops', 'min_iops', 'log_disk_size',
                                        'iops_weight', 'tenant_role'],
            lambda x: [x['TENANT_NAME'], x['TENANT_TYPE'], x['COMPATIBILITY_MODE'], x['PRIMARY_ZONE'],
                       x['MAX_CPU'], x['MIN_CPU'], str(Capacity(x['MEMORY_SIZE'])), x['MAX_IOPS'], x['MIN_IOPS'],
                       str(Capacity(x['LOG_DISK_SIZE'])), x['IOPS_WEIGHT'], x['TENANT_ROLE']],
            title='tenant base info')
    else:
        stdio.stop_loading('fail')
        plugin_context.return_false()

    if standby_tenants:
        stdio.print_list(standby_tenants, ['standby_tenant_name', 'tenant_status', 'sync_status', 'sync_scn_timestamp', 'err_code', 'error_comment', 'switchover_status', 'switchover_epoch', 'log_mode'],
            lambda x: [x.get('TENANT_NAME', ''), x.get('STATUS', ''), x.get('SYNC_STATUS', ''), datetime.datetime.fromtimestamp(x.get('SYNC_SCN') / 1000000000) if x.get('SYNC_SCN', '') else '', x.get('ERR_CODE', ''), x.get('ERROR_COMMENT', ''), x.get('SWITCHOVER_STATUS', ''), x.get('SWITCHOVER_EPOCH', ''), x.get('LOG_MODE', '')],
            title='standby tenant standby info')
        stdio.print_list(standby_tenants, ['standby_tenant_name', 'primary_tenant_info'],
            lambda x: [x.get('TENANT_NAME', ''), x.get('PRIMARY_TENANT_INFO', '')],
            title='standby tenant`s primary info')

    plugin_context.set_variable('need_list_standby', need_list_standby)
    return plugin_context.return_true()