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
if sys.version_info.major == 2:
    import MySQLdb as mysql
else:
    import pymysql as mysql


stdio = None


def _connect(ip, port, user, password=''):
    stdio.verbose('connect %s -P%s -u%s -p%s' % (ip, port, user, password))
    if sys.version_info.major == 2:
        db = mysql.connect(host=ip, user=user, port=int(port), passwd=str(password))
        cursor = db.cursor(cursorclass=mysql.cursors.DictCursor)
    else:
        db = mysql.connect(host=ip, user=user, port=int(port), password=str(password), cursorclass=mysql.cursors.DictCursor)
        cursor = db.cursor()
    return db, cursor


def connect(plugin_context, target_server=None, sys_root=True, *args, **kwargs):
    global stdio
    count = 10
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    if target_server:
        servers = [target_server]
        server_config = cluster_config.get_server_conf(target_server)
        stdio.start_loading('Connect obproxy(%s:%s)' % (target_server, server_config['listen_port']))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to obproxy')
    if sys_root:
        user = 'root@proxysys'
    else:
        user = 'root'
    dbs = {}
    cursors = {}
    while count and servers:
        count -= 1
        tmp_servers = []
        for server in servers:
            try:
                server_config = cluster_config.get_server_conf(server)
                pwd_key = 'obproxy_sys_password' if sys_root else 'observer_sys_password'
                db, cursor = _connect(server.ip, server_config['listen_port'], user, server_config.get(pwd_key, '') if count % 2 else '')
                dbs[server] = db
                cursors[server] = cursor
            except:
                tmp_servers.append(server)
                pass
        servers = tmp_servers
        servers and time.sleep(3)
    
    if  servers:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        if target_server:
            return plugin_context.return_true(connect=dbs[target_server], cursor=cursors[target_server])
        else:
            return plugin_context.return_true(connect=dbs, cursor=cursors)