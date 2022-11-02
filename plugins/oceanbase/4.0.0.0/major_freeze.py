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

    def execute(cursor, query, args=None):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose('execute sql: %s' % msg)
        stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            cursor.execute(query, args)
            return cursor.fetchone()
        except:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    stdio = plugin_context.stdio
    tenant_name = kwargs.get('tenant')
    tenant_id = execute(cursor, "select TENANT_ID from oceanbase.DBA_OB_TENANTS where tenant_name = '%s'" % tenant_name)["TENANT_ID"]
    # Major freeze
    stdio.start_loading('Merge')
    sql_frozen_scn = "select FROZEN_SCN, LAST_SCN from oceanbase.CDB_OB_MAJOR_COMPACTION where tenant_id = '%s'" % tenant_id
    merge_version = execute(cursor, sql_frozen_scn)['FROZEN_SCN']
    execute(cursor, "alter system major freeze tenant = %s" % tenant_name)
    while True:
        current_version = execute(cursor, sql_frozen_scn).get("FROZEN_SCN")
        if int(current_version) > int(merge_version):
            break
        time.sleep(5)
    while True:
        ret = execute(cursor, sql_frozen_scn)
        if int(ret.get("FROZEN_SCN", 0)) / 1000 == int(ret.get("LAST_SCN", 0)) / 1000:
            break
        time.sleep(5)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
