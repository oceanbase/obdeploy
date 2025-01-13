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

from tool import Cursor


def cursor_check(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio

    depend_conf = plugin_context.get_variable('binlog_config')
    host = depend_conf.get('database_ip')
    port = depend_conf.get('database_port')
    username = depend_conf.get('user')
    password = depend_conf.get('password')
    binlog_cursor = None
    connected = False
    retries = 30
    while not connected and retries:
        retries -= 1
        try:
            binlog_cursor = Cursor(ip=host, port=port, user=username, tenant='', password=password, stdio=stdio)
            connected = True
            break
        except:
            time.sleep(1)
    if not connected:
        stdio.error("failed to connect binlog meta db")
        return plugin_context.return_false()
    return plugin_context.return_true(binlog_cursor=binlog_cursor)