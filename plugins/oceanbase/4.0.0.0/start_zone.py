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


def start_zone(plugin_context, zone, *args, **kwargs):

    stdio = plugin_context.stdio
    restart_manager = plugin_context.get_variable('restart_manager')

    if zone:
        restart_manager.close()
    if not restart_manager.connect():
        stdio.stop_loading('stop_loading', 'fail')
        return plugin_context.return_false()
    if zone:
        stdio.verbose('start zone %s' % zone)
        start_sql = "alter system start zone %s" % zone
        check_sql = "select * from oceanbase.__all_zone where name = 'status' and zone = '%s' and info != 'ACTIVE'" % zone
        while True:
            if restart_manager.execute_sql(start_sql, error=False) is None:
                break
            if restart_manager.execute_sql(check_sql, error=False) is None:
                break
            time.sleep(3)
    if not restart_manager.connect():
        return plugin_context.return_false()
    stdio.verbose('server check')
    restart_manager.broken_sql("select * from oceanbase.__all_server where status != 'active' or stop_time > 0 or start_service_time = 0")


    return plugin_context.return_true()