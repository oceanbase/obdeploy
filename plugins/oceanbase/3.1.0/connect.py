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
import re
from copy import copy
if sys.version_info.major == 2:
    import MySQLdb as mysql
else:
    import pymysql as mysql

import const
from _errno import EC_FAIL_TO_CONNECT
from _stdio import SafeStdio
from tool import Cursor


def connect(plugin_context, target_server=None, retry_times=101, connect_all=False, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)

    if kwargs.get('scale_out_component') == const.COMP_OCP_SERVER_CE:
        cursor = plugin_context.get_return('cursor_check', spacename=const.COMP_OCP_SERVER_CE).get_return('cursor')
        if cursor:
            return return_true(connect=cursor.db, cursor=cursor, server=None)
    
    count = retry_times
    cluster_config = plugin_context.cluster_config
    new_cluster_config = kwargs.get("new_cluster_config")
    stdio = plugin_context.stdio
    if target_server:
        servers = [target_server]
        server_config = cluster_config.get_server_conf(target_server)
        stdio.start_loading('Connect observer(%s:%s)' % (target_server, server_config['mysql_port']))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to observer')
    while count:
        count -= 1
        connect_nums = 0
        for server in servers:
            try:
                server_config = cluster_config.get_server_conf(server)
                new_pwd = ''
                if new_cluster_config:
                    new_config = new_cluster_config.get_server_conf(server)
                    if new_config:
                        new_pwd = new_config['root_password']
                password = server_config.get('root_password', '')
                password = new_pwd if count % 2 else password
                cursor = Cursor(ip=server.ip, port=server_config.get('mysql_port', 2881), tenant='', password=password if password is not None else '', stdio=stdio)
                if cursor.execute('select 1', raise_exception=False, exc_level='verbose'):
                    if not connect_all:
                        stdio.stop_loading('succeed', text='Connect to observer {}:{}'.format(server.ip, server_config.get('mysql_port', 2881)))
                        return return_true(connect=cursor.db, cursor=cursor, server=server)
                    else:
                        connect_nums += 1
                        if connect_nums == len(servers):
                            stdio.stop_loading('succeed')
                            return return_true(connect=cursor.db, cursor=cursor, server=server)
            except:
                if count == 0:
                    stdio.exception('')
                if connect_all:
                    break
        time.sleep(3)

    stdio.stop_loading('fail')
    stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
    plugin_context.return_false()
