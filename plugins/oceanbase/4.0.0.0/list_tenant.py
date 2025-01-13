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

from _types import Capacity


def list_tenant(plugin_context, cursor, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    stdio.start_loading('Select tenant')
    tenant_infos = []
    sql = "select * from oceanbase.DBA_OB_TENANTS;"
    tenants = cursor.fetchall(sql)
    if tenants is False:
        stdio.stop_loading('fail')
        return

    for tenant in tenants:
        select_resource_pools_sql = "select UNIT_CONFIG_ID from oceanbase.DBA_OB_RESOURCE_POOLS where TENANT_ID = {};"
        if tenant['TENANT_TYPE'] == 'META':
            continue
        res = cursor.fetchone(select_resource_pools_sql.format(tenant['TENANT_ID']))
        if res is False:
            stdio.stop_loading('fail')
            return
        select_unit_configs_sql = "select * from oceanbase.DBA_OB_UNIT_CONFIGS where UNIT_CONFIG_ID = {};"
        res = cursor.fetchone(select_unit_configs_sql.format(res['UNIT_CONFIG_ID']))
        if res is False:
            stdio.stop_loading('fail')
            return
        tenant_infos.append(dict(tenant, **res))
    if tenant_infos:
        stdio.print_list(tenant_infos, ['tenant_name', 'tenant_type', 'compatibility_mode', 'primary_zone', 'max_cpu',
                                        'min_cpu', 'memory_size', 'max_iops', 'min_iops', 'log_disk_size',
                                        'iops_weight'],
            lambda x: [x['TENANT_NAME'], x['TENANT_TYPE'], x['COMPATIBILITY_MODE'], x['PRIMARY_ZONE'],
                       x['MAX_CPU'], x['MIN_CPU'], str(Capacity(x['MEMORY_SIZE'])), x['MAX_IOPS'], x['MIN_IOPS'],
                       str(Capacity(x['LOG_DISK_SIZE'])), x['IOPS_WEIGHT']],
            title='tenant')
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')
    plugin_context.return_false()