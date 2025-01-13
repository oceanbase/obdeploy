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

    sql = "select * from oceanbase.gv$tenant where tenant_name = '%s'" % tenant_name
    tenant = cursor.fetchone(sql)
    if tenant is False:
        return
    if not tenant:
        error('No such Tenant %s' % tenant_name)
        return

    sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d" % tenant['tenant_id']
    pool = cursor.fetchone(sql)
    if pool is False:
        error()
        return
    sql = "drop tenant %s FORCE" % tenant_name
    res = cursor.execute(sql)
    if res is False:
        error()
        return
    if not pool:
        error()
        return
    sql = "drop resource pool %s" % pool['name']
    res = cursor.execute(sql)
    if res is False:
        error()
        return

    sql = "select * from oceanbase.__all_unit_config where unit_config_id = %d" % pool['unit_config_id']
    unit = cursor.fetchone(sql)
    if not unit:
        error()
        return
    sql = "drop resource unit %s" % unit['name']
    res = cursor.execute(sql)
    if res is False:
        error()
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
    