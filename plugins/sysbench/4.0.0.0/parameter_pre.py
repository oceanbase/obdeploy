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


def parameter_pre(plugin_context, *args, **kwargs):
    tenant_sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    tenant_id = "TENANT_ID"

    plugin_context.set_variable('tenant_sql', tenant_sql)
    plugin_context.set_variable('tenant_id', tenant_id)

    return plugin_context.return_true()
