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


def parameter_pre(plugin_context, *args, **kwargs):
    tenant_sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    tenant_id = "TENANT_ID"

    plugin_context.set_variable('tenant_sql', tenant_sql)
    plugin_context.set_variable('tenant_id', tenant_id)

    return plugin_context.return_true()
