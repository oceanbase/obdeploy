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


def stop_zone(plugin_context, zone, *args, **kwargs):
    stdio = plugin_context.stdio
    restart_manager = plugin_context.get_variable('restart_manager')

    if not restart_manager.connect():
        return plugin_context.return_false()

    stdio.verbose('server check')
    restart_manager.broken_sql("select * from oceanbase.__all_server where status != 'active' or stop_time > 0 or start_service_time = 0")

    stdio.verbose('stop zone %s' % zone)
    stop_sql = "alter system stop zone %s" % zone
    check_sql = "select * from oceanbase.__all_zone where name = 'status' and zone = '%s' and info = 'ACTIVE'" % zone
    while True:
        if restart_manager.execute_sql(stop_sql, error=False) is None:
            break
        if restart_manager.execute_sql(check_sql, error=False):
            break
        time.sleep(3)

    return plugin_context.return_true()