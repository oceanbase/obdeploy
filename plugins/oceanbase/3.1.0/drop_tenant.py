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
    