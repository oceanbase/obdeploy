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

import sys
import time
from prettytable import PrettyTable


def display(plugin_context, cursor, *args, **kwargs):
    count = 10
    stdio = plugin_context.stdio
    stdio.start_loading('Wait for observer init')
    while count > 0:
        try:
            cursor.execute('select * from oceanbase.__all_server')
            servers = cursor.fetchall()
            if servers:
                stdio.print_list(servers, ['ip', 'version', 'port', 'zone', 'status'], 
                    lambda x: [x['svr_ip'], x['build_version'].split('_')[0], x['inner_port'], x['zone'], x['status']], title='observer')
                stdio.stop_loading('succeed')
                return plugin_context.return_true()
        except Exception as e:
            if e.args[0] != 1146:
                raise e
            count -= 1
            time.sleep(3)
    stdio.stop_loading('fail', 'observer need bootstarp')
    plugin_context.return_false()
