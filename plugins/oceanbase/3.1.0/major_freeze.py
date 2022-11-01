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
    merge_version = execute(cursor, "select value from oceanbase.__all_zone where name='frozen_version'")['value']
    stdio.start_loading('Merge')
    execute(cursor, 'alter system major freeze')
    sql = "select value from oceanbase.__all_zone where name='frozen_version' and value != %s" % merge_version
    while True:
        if execute(cursor, sql):
            break
        time.sleep(1)

    while True:
        if not execute(cursor, """select * from  oceanbase.__all_zone 
                    where name='last_merged_version'
                    and value != (select value from oceanbase.__all_zone where name='frozen_version' limit 1)
                    and zone in (select zone from  oceanbase.__all_zone where name='status' and info = 'ACTIVE')
                    """):
            break
        time.sleep(5)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
