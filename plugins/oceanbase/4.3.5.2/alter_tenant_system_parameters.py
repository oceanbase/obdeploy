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
from tool import exec_sql_in_tenant

def alter_tenant_system_parameters(plugin_context, cursor, create_tenant_options=[], *args, **kwargs):
    stdio = plugin_context.stdio
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    for options in multi_options:
        tenant_name = getattr(options, 'tenant_name', 'test')
        mode = getattr(options, 'mode', 'mysql').lower()
        root_password = getattr(options, tenant_name + '_root_password', "")
        system_parameters = kwargs.get('system_parameters')
        sql = "ALTER SYSTEM SET {} = '{}'"
        if system_parameters:
            for parameter in system_parameters:
                sql = sql.format(parameter, system_parameters[parameter])
                res = exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=tenant_name, mode=mode, password=root_password if root_password else '', stdio=stdio)
                if not res:
                    stdio.warn("Failed to modify tenant-level parameter %s" % parameter)
    return plugin_context.return_true()
