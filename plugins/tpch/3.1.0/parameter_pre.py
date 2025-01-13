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

import os

from tool import set_plugin_context_variables


def parameter_pre(plugin_context, *args, **kwargs):
    tenant_sql = "select * from oceanbase.gv$tenant where tenant_name = %s"

    tenant_id = "tenant_id"

    local_dir, _ = os.path.split(__file__)
    ddl_path = os.path.join(local_dir, 'create_tpch_mysql_table_part.ddl')

    variables_dict = {
        'tenant_sql': tenant_sql,
        'tenant_id': tenant_id,
        'ddl_path': ddl_path
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()
