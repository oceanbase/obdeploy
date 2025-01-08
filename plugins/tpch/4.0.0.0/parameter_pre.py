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

import os

from tool import set_plugin_context_variables


def parameter_pre(plugin_context, *args, **kwargs):
    tenant_sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"

    tenant_id = "TENANT_ID"
    min_memory = 1073741824

    local_dir, _ = os.path.split(__file__)
    ddl_path = os.path.join(local_dir, 'create_tpch_mysql_table_part.ddl')

    variables_dict = {
        'tenant_sql': tenant_sql,
        'tenant_id': tenant_id,
        'min_memory': min_memory,
        'ddl_path': ddl_path
    }

    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()
