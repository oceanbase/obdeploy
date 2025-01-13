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


def drop_tenant(plugin_context, cursor, *args, **kwargs):
    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')
        
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    options = plugin_context.options

    tenant_name = getattr(options, 'tenant_name', '')
    if not tenant_name:
        error('Pease set tenant name')
        return
    elif tenant_name == 'sys':
        error('Prohibit deleting sys tenant')
        return

    stdio.start_loading('Drop tenant %s' % tenant_name)

    tenant = None
    sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = %s"
    tenant = cursor.fetchone(sql, [tenant_name])
    if tenant is False:
        return
    if not tenant:
        error('No such Tenant %s' % tenant_name)
        return

    pool = None
    sql = "select * from oceanbase.DBA_OB_RESOURCE_POOLS where tenant_id = %d" % tenant['TENANT_ID']
    pool = cursor.fetchone(sql)
    if pool is False:
        return
    sql = "drop tenant %s FORCE" % tenant_name
    res = cursor.execute(sql)
    if res is False:
        error()
        return
    if not pool:
        error()
        return
    sql = "drop resource pool %s" % pool['NAME']
    res = cursor.execute(sql)
    if res is False:
        error()
        return

    sql = "select * from oceanbase.DBA_OB_UNIT_CONFIGS where unit_config_id = %d" % pool['UNIT_CONFIG_ID']
    unit = cursor.fetchone(sql)
    if not unit:
        return
    sql = "drop resource unit %s" % unit['NAME']
    res = cursor.execute(sql)
    if res is False:
        error()
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
    