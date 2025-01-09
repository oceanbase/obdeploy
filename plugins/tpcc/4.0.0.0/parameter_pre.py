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
    active_sql = "select b.CPU_CAPACITY from oceanbase.DBA_OB_SERVERS a join oceanbase.GV$OB_SERVERS b on a.SVR_IP=b.SVR_IP and a.SVR_PORT = b.SVR_PORT where a.STATUS = 'ACTIVE' and a.STOP_TIME is NULL  and a.START_SERVICE_TIME > 0"
    tenant_sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    resource_sql = "select * from oceanbase.DBA_OB_RESOURCE_POOLS where TENANT_ID = %d"
    unit_sql = "select * from oceanbase.DBA_OB_UNIT_CONFIGS where UNIT_CONFIG_ID = %d"

    cpu_count_key = 'CPU_CAPACITY'
    cpu_count_value = 0
    tenant_id = 'TENANT_ID'
    unit_config_id = 'UNIT_CONFIG_ID'
    max_memory = 'MEMORY_SIZE'
    max_cpu = 'MAX_CPU'
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
