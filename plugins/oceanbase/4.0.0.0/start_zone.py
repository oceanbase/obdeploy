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