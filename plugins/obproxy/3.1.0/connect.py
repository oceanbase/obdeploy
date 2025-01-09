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
from copy import copy
if sys.version_info.major == 2:
    import MySQLdb as mysql
else:
    import pymysql as mysql

from _errno import EC_FAIL_TO_CONNECT, EC_SQL_EXECUTE_FAILED
from _stdio import SafeStdio


class Cursor(SafeStdio):

    def __init__(self, ip, port, user='root', tenant='sys', password='', stdio=None):
        self.stdio = stdio
        self.ip = ip
        self.port = port
        self._user = user
        self.tenant = tenant
        self.password = password
        self.cursor = None
        self.db = None
        self._connect()
        self._raise_exception = False
        self._raise_cursor = None

    @property
    def user(self):
        if "@" in self._user:
            return self._user
        if self.tenant:
            return "{}@{}".format(self._user, self.tenant)
        else:
            return self._user

    @property
    def raise_cursor(self):
        if self._raise_cursor:
            return self._raise_cursor
        raise_cursor = copy(self)
        raise_cursor._raise_exception = True
        self._raise_cursor = raise_cursor
        return raise_cursor

    if sys.version_info.major == 2:
        def _connect(self):
            self.stdio.verbose('connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
            self.db = mysql.connect(host=self.ip, user=self.user, port=int(self.port), passwd=str(self.password))
            self.cursor = self.db.cursor(cursorclass=mysql.cursors.DictCursor)
    else:
        def _connect(self):
            self.stdio.verbose('connect %s -P%s -u%s -p%s' % (self.ip, self.port, self.user, self.password))
            self.db = mysql.connect(host=self.ip, user=self.user, port=int(self.port), password=str(self.password),
                                    cursorclass=mysql.cursors.DictCursor)
            self.cursor = self.db.cursor()

    def new_cursor(self, tenant='sys', user='root', password='', ip='', port='', print_exception=True):
        try:
            ip = ip if ip else self.ip
            port = port if port else self.port
            return Cursor(ip=ip, port=port, user=user, tenant=tenant, password=password, stdio=self.stdio)
        except:
            print_exception and self.stdio.exception('')
            self.stdio.verbose('fail to connect %s -P%s -u%s@%s  -p%s' % (self.ip, self.port, user, tenant, password))
            return None

    def execute(self, sql, args=None, execute_func=None, raise_exception=False, exc_level='error', stdio=None):
        try:
            stdio.verbose('execute sql: %s. args: %s' % (sql, args))
            self.cursor.execute(sql, args)
            if not execute_func:
                return self.cursor
            return getattr(self.cursor, execute_func)()
        except Exception as e:
            getattr(stdio, exc_level)(EC_SQL_EXECUTE_FAILED.format(sql=sql))
            if raise_exception is None:
                raise_exception = self._raise_exception
            if raise_exception:
                stdio.exception('')
                raise e
            return False

    def fetchone(self, sql, args=None, raise_exception=False, exc_level='error', stdio=None):
        return self.execute(sql, args=args, execute_func='fetchone', raise_exception=raise_exception, exc_level=exc_level, stdio=stdio)

    def fetchall(self, sql, args=None, raise_exception=False, exc_level='error', stdio=None):
        return self.execute(sql, args=args, execute_func='fetchall', raise_exception=raise_exception, exc_level=exc_level, stdio=stdio)

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.db:
            self.db.close()
            self.db = None


def connect(plugin_context, target_server=None, connect_proxysys=True, *args, **kwargs):
    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)
    
    count = 10
    cluster_config = plugin_context.cluster_config
    new_cluster_config = kwargs.get("new_cluster_config")
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
        if connect_proxysys:
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
                if connect_proxysys:
                    pwd_key = 'obproxy_sys_password'
                else:
                    pwd_key = 'observer_root_password'
                new_config = None
                if new_cluster_config:
                    new_config = new_cluster_config.get_server_conf(server)
                    if new_config:
                        new_r_password = new_config[pwd_key]
                r_password = password if password else server_config.get(pwd_key)
                r_password = new_r_password if new_config and count % 2 else r_password
                if r_password is None:
                    r_password = ''

                cursor = Cursor(ip=server.ip, port=server_config['listen_port'], user=user, tenant='', password=r_password if count % 2 else '', stdio=stdio)
                if user in ['root', 'root@sys']:
                    if not cursor.fetchone('select * from information_schema.TABLES limit 1'):
                        continue
                dbs[server] = cursor.db
                cursors[server] = cursor
            except:
                tmp_servers.append(server)
                pass
        servers = tmp_servers
        servers and time.sleep(3)

    if servers:
        stdio.stop_loading('fail')
        stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.set_variable('cursor', cursor)
        if target_server:
            return return_true(connect=dbs[target_server], cursor=cursors[target_server])
        else:
            return return_true(connect=dbs, cursor=cursors)