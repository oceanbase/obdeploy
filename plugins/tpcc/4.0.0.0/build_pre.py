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
