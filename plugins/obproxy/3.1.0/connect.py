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


def execute(cursor, query, args=None):
    msg = query % tuple(args) if args is not None else query
    stdio.verbose('execute sql: %s' % msg)
    # stdio.verbose("query: %s. args: %s" % (query, args))
    try:
        cursor.execute(query, args)
        return cursor.fetchone()
    except:
        msg = 'execute sql exception: %s' % msg
        stdio.exception(msg)
        raise Exception(msg)


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
    user = kwargs.get('user')
    password = kwargs.get('password')
    if not user:
        if sys_root:
            user = 'root@proxysys'
        else:
            user = 'root'

    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            ob_config = cluster_config.get_depend_config(comp)
            if not ob_config:
                continue
            odp_config = cluster_config.get_global_conf()
            config_map = {
                'observer_sys_password': 'proxyro_password',
                'cluster_name': 'appname',
                'observer_root_password': 'root_password'
            }
            for key in config_map:
                ob_key = config_map[key]
                if key not in odp_config and ob_key in ob_config:
                    cluster_config.update_global_conf(key, ob_config.get(ob_key), save=False)
            break
    dbs = {}
    cursors = {}
    while count and servers:
        count -= 1
        tmp_servers = []
        for server in servers:
            try:
                server_config = cluster_config.get_server_conf(server)
                if sys_root:
                    pwd_key = 'obproxy_sys_password'
                else:
                    pwd_key = 'observer_root_password'
                r_password = password if password else server_config.get(pwd_key)
                if r_password is None:
                    r_password = ''
                db, cursor = _connect(server.ip, server_config['listen_port'], user, r_password if count % 2 else '')
                if user in ['root', 'root@sys']:
                    stdio.verbose('execute sql: select * from information_schema.TABLES limit 1')
                    cursor.execute('select * from information_schema.TABLES limit 1')
                    stdio.verbose("result: {}".format(cursor.fetchone()))
                dbs[server] = db
                cursors[server] = cursor
            except:
                tmp_servers.append(server)
                pass
        servers = tmp_servers
        servers and time.sleep(3)
    
    if servers:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        if target_server:
            return plugin_context.return_true(connect=dbs[target_server], cursor=cursors[target_server])
        else:
            return plugin_context.return_true(connect=dbs, cursor=cursors)