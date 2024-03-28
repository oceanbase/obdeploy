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