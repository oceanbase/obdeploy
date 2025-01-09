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

from tool import set_plugin_context_variables


def build_pre(plugin_context, *args, **kwargs):
    server_status_sql = "select * from oceanbase.DBA_OB_SERVERS where STATUS != 'ACTIVE' or STOP_TIME is not NULL or START_SERVICE_TIME is NULL"
    server_state = ['DETECT_ALIVE', 'ACTIVE']

    def merge(plugin_context, stdio, cursor, tenant_name):
        pre_test_ret = plugin_context.get_return("pre_test")
        tenant_id = pre_test_ret.get_return("tenant_id")

        # Major freeze
        stdio.start_loading('Merge')
        sql_frozen_scn = "select FROZEN_SCN, LAST_SCN from oceanbase.CDB_OB_MAJOR_COMPACTION where tenant_id = %s" % tenant_id
        merge_version = cursor.fetchone(sql_frozen_scn)
        if merge_version is False:
            return False
        merge_version = merge_version['FROZEN_SCN']
        if cursor.fetchone("alter system major freeze tenant = %s" % tenant_name) is False:
            return False
        # merge version changed
        while True:
            current_version = cursor.fetchone(sql_frozen_scn)
            if current_version is False:
                return False
            current_version = current_version['FROZEN_SCN']
            if int(current_version) > int(merge_version):
                break
            time.sleep(5)
        stdio.verbose('current merge version is: %s' % current_version)
        # version updated
        while True:
            ret = cursor.fetchone(sql_frozen_scn)
            if ret is False:
                return False
            if int(ret.get("FROZEN_SCN", 0)) / 1000 == int(ret.get("LAST_SCN", 0)) / 1000:
                break
            time.sleep(5)
        stdio.stop_loading('succeed')
        return True

    variables_dict = {
        'server_status_sql': server_status_sql,
        'server_state': server_state,
        'merge': merge
    }

    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()
