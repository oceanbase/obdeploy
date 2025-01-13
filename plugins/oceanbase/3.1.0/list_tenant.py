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
    sql = "select * from oceanbase.gv$tenant;"
    tenants = cursor.fetchall(sql)
    if tenants is False:
        stdio.stop_loading('fail')
        return
    for tenant in tenants:
        select_resource_pools_sql = "select unit_config_id from oceanbase.__all_resource_pool where tenant_id = {};"
        res = cursor.fetchone(select_resource_pools_sql.format(tenant['tenant_id']))
        if res is False:
            stdio.stop_loading('fail')
            return
        select_unit_configs_sql = "select * from oceanbase.__all_unit_config where unit_config_id = {};"
        res = cursor.fetchone(select_unit_configs_sql.format(res['unit_config_id']))
        if res is False:
            stdio.stop_loading('fail')
            return
        tenant_infos.append(dict(tenant, **res))
    if tenant_infos:
        stdio.print_list(tenant_infos, ['tenant_name', 'zone_list', 'primary_zone', 'max_cpu', 'min_cpu', 'max_memory',
                                        'min_memory', 'max_iops', 'min_iops', 'max_disk_size', 'max_session_num'],
                         lambda x: [x['tenant_name'], x['zone_list'], x['primary_zone'], x['max_cpu'], x['min_cpu'],
                                    str(Capacity(x['max_memory'])), str(Capacity(x['min_memory'])), x['max_iops'],
                                    x['min_iops'], str(Capacity(x['max_disk_size'])), x['max_session_num']],
                         title='tenant')
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')
    plugin_context.return_false()