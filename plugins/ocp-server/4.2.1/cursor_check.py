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

import re
import time

import _errno as err
from tool import Cursor


def cursor_check(plugin_context, need_connect=True, *args, **kwargs):
    error = plugin_context.get_variable('error')

    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    env = plugin_context.get_variable('start_env')
    server = cluster_config.servers[0]
    server_config = env[server]
    jdbc_url = server_config.get('jdbc_url', None)
    success = True
    cursor = ''
    meta_cursor = ''
    monitor_cursor = ''
    if jdbc_url:
        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
        if not matched:
            stdio.error('jdbc_url is not valid')
            return plugin_context.return_false()
        host = matched.group(1)
        port = matched.group(2)[1:]
        database = matched.group(3)
        user = server_config['jdbc_username']
        password = server_config['jdbc_password']
        meta_user = server_config['ocp_meta_username']
        meta_tenant = server_config['ocp_meta_tenant']['tenant_name']
        meta_password = server_config['ocp_meta_password']
        monitor_user = server_config['ocp_monitor_username']
        monitor_tenant = server_config['ocp_monitor_tenant']['tenant_name']
        monitor_password = server_config['ocp_monitor_password']
        connected = False
        cursor = None
        retries = 100
        while not connected and retries:
            retries -= 1
            try:
                cursor = Cursor(ip=host, port=port, user=user, password=password, stdio=stdio)
                if need_connect:
                    meta_cursor = Cursor(host, port, meta_user, meta_tenant, meta_password, stdio)
                    meta_cursor.execute("show databases;", raise_exception=False, exc_level='verbose')
                    monitor_cursor = Cursor(host, port, monitor_user, monitor_tenant, monitor_password, stdio)
                    monitor_cursor.execute("show databases;", raise_exception=False, exc_level='verbose')
                connected = True
                stdio.verbose('check cursor passed')
            except:
                stdio.verbose('check cursor failed')
                time.sleep(1)
            if not connected:
                success = False
                error('metadb connect', err.EC_OCP_SERVER_CONNECT_METADB, [err.SUG_OCP_SERVER_JDBC_URL_CONFIG_ERROR])

        if need_connect:
            if meta_cursor and meta_user != 'root':
                sql = f"""ALTER USER root IDENTIFIED BY %s"""
                meta_cursor.execute(sql, args=[meta_password], raise_exception=False, exc_level='verbose')

            if monitor_cursor and monitor_user != 'root':
                sql = f"""ALTER USER root IDENTIFIED BY %s"""
                monitor_cursor.execute(sql, args=[monitor_password], raise_exception=False, exc_level='verbose')

        plugin_context.set_variable('meta_cursor', meta_cursor)
        plugin_context.set_variable('jdbc_host', host)
        plugin_context.set_variable('jdbc_port', port)
        plugin_context.set_variable('monitor_cursor', monitor_cursor)
        plugin_context.set_variable('cursor', cursor)
    plugin_context.set_variable('success', success)
    return plugin_context.return_true(cursor=cursor)