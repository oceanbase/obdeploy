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


def active_check(plugin_context,  *args, **kwargs):
    
    stdio = plugin_context.stdio
    restart_manager = plugin_context.get_variable('restart_manager')

    stdio.start_loading('Observer active check')
    if not restart_manager.connect():
        stdio.stop_loading('stop_loading', 'fail')
        return plugin_context.return_false()

    while restart_manager.execute_sql(
            "select * from oceanbase.__all_virtual_clog_stat where table_id = 1099511627777 and status != 'ACTIVE'",
            error=False):
        time.sleep(3)
    stdio.stop_loading('stop_loading', 'success')
    return plugin_context.return_true()