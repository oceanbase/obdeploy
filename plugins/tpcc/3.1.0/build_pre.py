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
    server_status_sql = "select * from oceanbase.__all_server where status != 'active' or stop_time > 0 or start_service_time = 0"
    server_state = ['ACTIVE']

    def merge(plugin_context, stdio, cursor, tenant_name):
        merge_version = cursor.fetchone("select value from oceanbase.__all_zone where name='frozen_version'")
        if merge_version is False:
            return False
        merge_version = merge_version['value']
        stdio.start_loading('Merge')
        if cursor.fetchone('alter system major freeze') is False:
            return False
        sql = "select value from oceanbase.__all_zone where name='frozen_version' and value != %s" % merge_version
        while True:
            res = cursor.fetchone(sql)
            if res is False:
                return False
            if res:
                break
            time.sleep(1)

        while True:
            res = cursor.fetchone("""select * from  oceanbase.__all_zone 
                                    where name='last_merged_version'
                                    and value != (select value from oceanbase.__all_zone where name='frozen_version' limit 1)
                                    and zone in (select zone from  oceanbase.__all_zone where name='status' and info = 'ACTIVE')
                                """)
            if res is False:
                return False
            if not res:
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
