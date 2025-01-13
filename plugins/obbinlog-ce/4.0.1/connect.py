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


def connect(plugin_context, *args, **kwargs):
    if plugin_context.get_variable('status_check_pass') is False:
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.start_loading('connect %s' % cluster_config.name)
    count = 101

    while count:
        count -= 1
        for server in cluster_config.servers:
            try:
                server_config = cluster_config.get_server_conf(server)
                cursor = Cursor(ip=server.ip, port=server_config.get('service_port'), user='', tenant='', stdio=stdio)
                if cursor.execute('select 1', raise_exception=False, exc_level='verbose'):
                    stdio.stop_loading('succeed', text='Connect to {} {}:{}'.format(cluster_config.name, server.ip,server_config.get('service_port')))
                    return plugin_context.return_true(binlog_cursor=cursor)
            except:
                if count == 0:
                    stdio.exception('')
        time.sleep(3)
    stdio.stop_loading('fail')
    return plugin_context.return_false()
