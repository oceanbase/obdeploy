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

import re


def parse_size(size):
    _bytes = 0
    if isinstance(size, str):
        size = size.strip()
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}
        match = re.match(r'^([1-9][0-9]*)\s*([B,K,M,G,T])$', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
    else:
        div = 1024
        format = '%d%s'
    while idx < 5 and size >= 1024:
        size /= 1024.0
        idx += 1
    return format % (size, units[idx])


def list_tenant(plugin_context, cursor, *args, **kwargs):

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    stdio.start_loading('Select tenant')
    tenant_infos = []
    sql = "select * from oceanbase.gv$tenant;"
    tenants = cursor.fetchall(sql)
    if tenants is False:
        stdio.stop_loading('fail')
        return
    for tenant in tenants:
        unit_name = '%s_unit' % tenant['tenant_name'] if tenant['tenant_name'] != 'sys' else 'sys_unit_config'
        sql = "select * from oceanbase.__all_unit_config where name = '%s'"
        res = cursor.fetchone(sql % unit_name)
        if res is False:
            stdio.stop_loading('fail')
            return
        tenant_infos.append(dict(tenant, **res))
    if tenant_infos:
        stdio.print_list(tenant_infos, ['tenant_name', 'zone_list', 'primary_zone', 'max_cpu', 'min_cpu', 'max_memory',
                                        'min_memory', 'max_iops', 'min_iops', 'max_disk_size', 'max_session_num'],
                         lambda x: [x['tenant_name'], x['zone_list'], x['primary_zone'], x['max_cpu'], x['min_cpu'],
                                    format_size(x['max_memory']), format_size(x['min_memory']), x['max_iops'],
                                    x['min_iops'], format_size(x['max_disk_size']), x['max_session_num']],
                         title='tenant')
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')
    plugin_context.return_false()