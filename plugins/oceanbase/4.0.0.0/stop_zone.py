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