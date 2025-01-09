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


import os

from tool import set_plugin_context_variables

def parameter_pre(plugin_context, *args, **kwargs):
    active_sql = "select a.id , b.cpu_total from oceanbase.__all_server a " \
                 "join oceanbase.__all_virtual_server_stat b on a.id=b.id " \
                 "where a.status = 'active' and a.stop_time = 0 and a.start_service_time > 0;"
    tenant_sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
    resource_sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d"
    unit_sql = "select * from oceanbase.__all_unit_config where unit_config_id = %d"

    cpu_count_key = 'cpu_total'
    cpu_count_value = 2
    tenant_id = 'tenant_id'
    unit_config_id = 'unit_config_id'
    max_memory = 'max_memory'
    max_cpu = 'max_cpu'
    sql_oceanbase_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sql.oceanbase')

    variables_dict = {
        'active_sql': active_sql,
        'tenant_sql': tenant_sql,
        'resource_sql': resource_sql,
        'unit_sql': unit_sql,
        'cpu_count_key': cpu_count_key,
        'tenant_id': tenant_id,
        'unit_config_id': unit_config_id,
        'cpu_count_value': cpu_count_value,
        'max_memory': max_memory,
        'max_cpu': max_cpu,
        'sql_oceanbase_path': sql_oceanbase_path
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()
