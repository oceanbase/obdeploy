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


MAJOR_FREEZE_TIMEOUT_SECONDS = 900


def major_freeze(plugin_context, cursor, *args, **kwargs):
    stdio = plugin_context.stdio
    stdio.start_loading('Merge')
    sql_frozen_scn = 'SELECT FROZEN_SCN, LAST_SCN FROM oceanbase.DBA_OB_MAJOR_COMPACTION'
    merge_version = cursor.fetchone(sql_frozen_scn)
    if merge_version is False:
        stdio.stop_loading('fail')
        stdio.error('Failed to query the current major compaction SCN.')
        return plugin_context.return_false()
    merge_version = merge_version['FROZEN_SCN']
    if cursor.execute('ALTER SYSTEM MAJOR FREEZE') is False:
        stdio.stop_loading('fail')
        stdio.error('Failed to trigger major freeze.')
        return plugin_context.return_false()
    deadline = time.time() + MAJOR_FREEZE_TIMEOUT_SECONDS
    while time.time() < deadline:
        current_version = cursor.fetchone(sql_frozen_scn)
        if current_version is False:
            stdio.stop_loading('fail')
            stdio.error('Failed to query major freeze progress.')
            return plugin_context.return_false()
        if int(current_version.get('FROZEN_SCN', 0)) > int(merge_version):
            break
        time.sleep(5)
    else:
        stdio.stop_loading('fail')
        stdio.error('Timed out waiting for the major freeze SCN to advance.')
        return plugin_context.return_false()
    while time.time() < deadline:
        result = cursor.fetchone(sql_frozen_scn)
        if result is False:
            stdio.stop_loading('fail')
            stdio.error('Failed to query major compaction progress.')
            return plugin_context.return_false()
        if int(result.get('FROZEN_SCN', 0)) // 1000 == int(result.get('LAST_SCN', 0)) // 1000:
            break
        time.sleep(5)
    else:
        stdio.stop_loading('fail')
        stdio.error('Timed out waiting for the major compaction to finish.')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
