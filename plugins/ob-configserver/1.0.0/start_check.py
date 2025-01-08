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

import os
import sys

if sys.version_info.major == 2:
    import MySQLdb as mysql
else:
    import pymysql as mysql

import _errno as err
from tool import get_port_socket_inode


stdio = None
success = True


def check_mysql_alive(url):
    """
    Check if MySQL is alive
    """

    status, data, msg = parse_url(url)

    if not status:
        return False, msg

    try:
        sql = "SELECT 1"
        if sys.version_info.major == 2:
            # python 2
            db = mysql.connect(host=data['host'], user=data['user'], port=int(data['port']), passwd=data['password'], database=data['dbname'])
            cursor = db.cursor(cursorclass=mysql.cursors.DictCursor)
            cursor.execute(sql)
            result = cursor.fetchone()
            db.close()
            return result, ''
        else:
            # python 3
            connection = mysql.connect(host=data['host'],
                                         user=data['user'],
                                         password=data['password'],
                                         database=data['dbname'],
                                         port=int(data['port']),
                                         charset='utf8mb4',
                                         cursorclass=mysql.cursors.DictCursor)

            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    return result, ''
    except Exception as e:
        return False, e


def parse_url(url):
    """
    parse url,return status, {user:xxx, password:xxx, host:xxx, port:xxx, dbname:xxx}, msg

    url:user:password@tcp(10.10.10.1:2883)/test?parseTime=true
    """

    user_index = url.find(':')
    if user_index == -1:
        return False, {}, 'connection_url near `user` format error'
    user = url[:user_index]
    url = url[user_index + 1:]

    password_index = url.find('@tcp(')
    if password_index == -1:
        return False, {}, 'connection_url near `password` format error'
    password = url[:password_index]
    url = url[password_index + 5:]

    host_index = url.find(':')
    if host_index == -1:
        return False, {}, 'connection_url near `host:port` format error'
    host = url[:host_index]
    url = url[host_index + 1:]

    port_index = url.find(')/')
    if port_index == -1:
        return False, {}, 'connection_url near `host:port` format error'
    port = url[:port_index]
    url = url[port_index + 2:]

    database_index = url.find('?')
    if database_index == -1:
        return False, {}, 'connection_url near `database` format error'
    dbname = url[:database_index]

    return True, {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
    }, ''


def start_check(plugin_context, init_check_status=False,  work_dir_check=False, work_dir_empty_check=True, precheck=False, *args, **kwargs):

    def check_pass(item):
        status = check_status.get(server).get(item).status
        if status == err.CheckStatus.WAIT:
            check_status.get(server).get(item).status = err.CheckStatus.PASS

    def wait_2_pass():
        status = check_status[server]
        for key in status:
            if status[key].status == err.CheckStatus.WAIT:
                status[key].status = err.CheckStatus.PASS

    def critical(item, error, suggests=[]):
        global success
        success = False
        status = check_status.get(server).get(item)
        status.status = err.CheckStatus.FAIL
        status.error = error
        status.suggests = suggests
        stdio.error(error)

    global stdio, success
    success = True
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_port = {}
    servers_dirs = {}
    servers_check_dirs = {}
    check_status = {}
    plugin_context.set_variable('start_check_status', check_status)

    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
            'parameter': err.CheckStatus(),
            'database': err.CheckStatus(),
            'vip': err.CheckStatus(),
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before start ob-configserver')

    global_config = cluster_config.get_global_conf()
    if len(cluster_config.servers) > 1 and (not global_config.get('vip_address') or not global_config.get('vip_port')):
        critical('vip', err.EC_OBC_MULTIPLE_SERVER_VIP_EMPTY_ERROR.format())

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        ip = server.ip
        client = clients[server]
        if not precheck:
            remote_pid_path = os.path.join(home_path, 'run/ob-configserver.pid')
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is runnning, skip' % server)
                    wait_2_pass()
                    continue

        if work_dir_check:
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            key = 'home_path'
            path = server_config.get(key)
            suggests = [err.SUG_CONFIG_CONFLICT_DIR.format(key=key, server=server)]
            if path in dirs and dirs[path]:
                critical('dir', err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']), suggests)
            dirs[path] = {
                'server': server,
                'key': key,
            }
            empty_check = work_dir_empty_check
            while True:
                if path in check_dirs:
                    if check_dirs[path] != True:
                        critical('dir', check_dirs[path], suggests)
                    break

                if client.execute_command('bash -c "[ -a %s ]"' % path):
                    is_dir = client.execute_command('[ -d {} ]'.format(path))
                    has_write_permission = client.execute_command('[ -w {} ]'.format(path))
                    if is_dir and has_write_permission:
                        if empty_check:
                            ret = client.execute_command('ls %s' % path)
                            if not ret or ret.stdout.strip():
                                check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=path))
                            else:
                                check_dirs[path] = True
                        else:
                            check_dirs[path] = True
                    else:
                        if not is_dir:
                            check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.NOT_DIR.format(path=path))
                        else:
                            check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=path))
                else:
                    path = os.path.dirname(path)
                    empty_check = False

        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]

        stdio.verbose('%s port check' % server)
        key = 'listen_port'
        port = int(server_config[key])
        if port in ports:
            critical(
                'port',
                err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                [err.SUG_PORT_CONFLICTS.format()]
            )
            continue
        ports[port] = {
            'server': server,
            'key': key
        }
        if get_port_socket_inode(client, port):
            critical(
                'port',
                err.EC_CONFLICT_PORT.format(server=ip, port=port),
                [err.SUG_USE_OTHER_PORT.format()]
            )
        check_pass('port')

        stdio.verbose('%s parameter check' % server)
        vip_address = server_config.get('vip_address')
        vip_port = server_config.get('vip_port')
        if (vip_address and not vip_port) or (not vip_address and vip_port):
            critical('parameter', err.EC_OBC_VIP_SET_ERROR.format(server=server))
        check_pass('parameter')

        stdio.verbose('%s database check' % server)
        storage_data = server_config.get('storage', {})
        database_type = storage_data.get('database_type')
        url = storage_data.get('connection_url')
        if database_type == 'mysql':
            if not url:
                critical('parameter', err.EC_OBC_CONNECTION_URL_EMPTY.format(server=server))
            rv, msg = check_mysql_alive(url)
            if not rv:
                stdio.verbose(msg)
                critical('database', err.EC_OBC_DATABASE_CONNECT_ERROR.format(server=server, url=url))
        elif database_type == 'sqlite3':
            if url:
                if not url.startswith('/'):
                    critical('parameter', err.EC_OBC_CONNECTION_URL_ERROR.format(server=server))
                sqlite_path = os.path.split(url)[0]
                if not client.execute_command('[ -w {} ]'.format(sqlite_path)):
                    critical('database', err.EC_OBC_SQLITE_PERMISSION_DENIED.format(ip=ip, path=sqlite_path))
        else:
            critical('parameter', err.EC_OBC_DATABASE_TYPE_ERROR.format(server=server))
        check_pass('database')

    for server in cluster_config.servers:
        wait_2_pass()

    if not success:
        stdio.stop_loading('fail')
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
