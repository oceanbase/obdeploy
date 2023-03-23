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

import time


def major_freeze(plugin_context, cursor, *args, **kwargs):

    stdio = plugin_context.stdio
    tenant_name = kwargs.get('tenant')
    tenant_id = cursor.fetchone("select TENANT_ID from oceanbase.DBA_OB_TENANTS where tenant_name = '%s'" % tenant_name)
    if tenant_id is False:
        return
    tenant_id = tenant_id["TENANT_ID"]
    # Major freeze
    stdio.start_loading('Merge')
    sql_frozen_scn = "select FROZEN_SCN, LAST_SCN from oceanbase.CDB_OB_MAJOR_COMPACTION where tenant_id = '%s'" % tenant_id
    merge_version = cursor.fetchone(sql_frozen_scn)
    if merge_version is False:
        return
    merge_version = merge_version['FROZEN_SCN']
    if cursor.execute("alter system major freeze tenant = %s" % tenant_name) is False:
        return
    while True:
        current_version = cursor.fetchone(sql_frozen_scn)
        if current_version is False:
            return
        current_version = current_version.get("FROZEN_SCN")
        if int(current_version) > int(merge_version):
            break
        time.sleep(5)
    while True:
        ret = cursor.fetchone(sql_frozen_scn)
        if ret is False:
            return
        if int(ret.get("FROZEN_SCN", 0)) / 1000 == int(ret.get("LAST_SCN", 0)) / 1000:
            break
        time.sleep(5)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
