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
    def is_authentication_error(exception):
        error_args = getattr(exception, 'args', ())
        error_code = error_args[0] if error_args else None
        try:
            if int(error_code) == 1045:
                return True
        except (TypeError, ValueError):
            pass
        error_message = ' '.join(str(arg) for arg in error_args).lower()
        return ('access denied' in error_message
                or 'authentication failed' in error_message)

    def get_corresponding_server_config(config, server):
        if not config:
            return {}
        try:
            server_config = config.get_server_conf(server)
        except Exception:
            server_config = None
        if server_config:
            return server_config
        for candidate in config.servers:
            if (getattr(candidate, 'name', None) == getattr(server, 'name', None)
                    or getattr(candidate, 'ip', None) == getattr(server, 'ip', None)):
                try:
                    return config.get_server_conf(candidate) or {}
                except Exception:
                    return {}
        return {}

    def return_true(**kwargs):
        for key, value in kwargs.items():
            plugin_context.set_variable(key, value)
        return plugin_context.return_true(**kwargs)

    if kwargs.get('scale_out_component') in const.COMPS_OCP:
        cursor = plugin_context.get_return('cursor_check', spacename=kwargs.get('scale_out_component')).get_return('cursor')
        if cursor:
            return return_true(connect=cursor.db, cursor=cursor, server=None)
    
    partial_retry_times = kwargs.get('partial_retry_times')
    if plugin_context.get_variable('status_check_pass') is False and partial_retry_times is not None:
        retry_times = partial_retry_times
    count = retry_times
    cluster_config = plugin_context.cluster_config
    new_cluster_config = kwargs.get("new_cluster_config")
    old_cluster_config = kwargs.get("old_cluster_config")
    stdio = plugin_context.stdio
    if target_server:
        servers = [target_server]
        server_config = cluster_config.get_server_conf(target_server)
        stdio.start_loading('Connect seekdb(%s:%s)' % (target_server, server_config['mysql_port']))
    else:
        servers = cluster_config.servers
        stdio.start_loading('Connect to seekdb')
    while count:
        count -= 1
        connected_cursors = []
        for server in servers:
            try:
                server_config = cluster_config.get_server_conf(server)
                configured_password = server_config.get('root_password', '')
                password_candidates = [
                    configured_password if configured_password is not None else ''
                ]
                for candidate_config in (old_cluster_config, new_cluster_config):
                    candidate = get_corresponding_server_config(
                        candidate_config, server)
                    if candidate:
                        candidate_password = candidate.get('root_password', '')
                        if candidate_password is None:
                            candidate_password = ''
                        if candidate_password not in password_candidates:
                            password_candidates.append(candidate_password)
                if '' not in password_candidates:
                    password_candidates.append('')
                connected_cursor = None
                for password in password_candidates:
                    cursor = None
                    try:
                        cursor = Cursor(
                            ip=server.ip,
                            port=server_config.get('mysql_port', 2881),
                            tenant='',
                            password=password if password is not None else '',
                            stdio=stdio)
                        if cursor.execute(
                                'select 1', raise_exception=False,
                                exc_level='verbose'):
                            connected_cursor = cursor
                            break
                    except Exception as e:
                        # Authentication failure can be raised by Cursor's
                        # constructor. Try the next transition password before
                        # treating this server as unreachable.
                        if is_authentication_error(e):
                            continue
                        raise
                    if cursor is not None:
                        try:
                            cursor.close()
                        except Exception:
                            pass
                        # Authentication already succeeded in Cursor's
                        # constructor. A failed probe is a connection/query
                        # problem, so changing the password cannot fix it.
                        break
                if connected_cursor is not None:
                    if not connect_all:
                        stdio.stop_loading('succeed', text='Connect to seekdb {}:{}'.format(server.ip, server_config.get('mysql_port', 2881)))
                        return return_true(
                            connect=connected_cursor.db,
                            cursor=connected_cursor, server=server)
                    connected_cursors.append(connected_cursor)
                    if len(connected_cursors) == len(servers):
                        for cursor in connected_cursors[:-1]:
                            try:
                                cursor.close()
                            except Exception:
                                pass
                        stdio.stop_loading('succeed')
                        return return_true(
                            connect=connected_cursor.db,
                            cursor=connected_cursor, server=server)
            except:
                if count == 0:
                    stdio.exception('')
                if connect_all:
                    break
        for cursor in connected_cursors:
            try:
                cursor.close()
            except Exception:
                pass
        time.sleep(3)

    stdio.stop_loading('fail')
    stdio.error(EC_FAIL_TO_CONNECT.format(component=cluster_config.name))
    plugin_context.return_false()
