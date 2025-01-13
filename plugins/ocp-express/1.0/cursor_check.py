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

from tool import Cursor


def cursor_check(plugin_context, *args, **kwargs):
    if not plugin_context.get_variable('clean_data') and kwargs.get('workflow_name', 'start') == 'destroy':
        return plugin_context.return_true()
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    added_components = cluster_config.get_deploy_added_components()
    env = plugin_context.get_variable('start_env')

    server = cluster_config.servers[0]
    server_config = env[server]
    jdbc_url = server_config['jdbc_url']
    jdbc_username = server_config['jdbc_username']
    jdbc_password = server_config['jdbc_password']
    success = True
    if jdbc_url:
        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
        if not matched:
            stdio.error("Invalid jdbc url: %s" % jdbc_url)
        ip = matched.group(1)
        sql_port = matched.group(2)[1:]
        database = matched.group(3)
        connect_infos = [[ip, sql_port]]
    else:
        connect_infos = server_config.get('connect_infos', '')
        database = server_config.get('ocp_meta_db', '')
    ob_cursor = None
    connected = False
    retries = 100
    tenant_map = {'meta@ocp_meta': {'user': 'meta@ocp', 'database': 'ocp_express'}, 'meta@ocp': {'user': 'meta@ocp_meta', 'database': 'ocp_meta'}}

    while not connected and retries:
        for connect_info in connect_infos:
            retries -= 1
            server_ip = connect_info[0]
            server_port = connect_info[-1]
            try:
                ob_cursor = Cursor(ip=server_ip, port=server_port, user=jdbc_username, password=jdbc_password, stdio=stdio)
                jdbc_url = 'jdbc:oceanbase://{}:{}/{}'.format(server_ip, server_port, database)
                stdio.verbose('jdbc_url: %s' % jdbc_url)
                connected = True
                if 'ocp-express' in added_components:
                    if ob_cursor.execute("select * from %s.config_properties limit 1" % database, exc_level='verbose'):
                        if not ob_cursor.execute("update %s.config_properties set `value`=NULL, default_value=NULL where `key`='ocp.version' or `key`='ocp.version.full'" % database, exc_level='verbose'):
                            stdio.verbose("failed to update 'ocp.version' and 'ocp.version.full' to NULL in config_properties table")
                            continue
                    if ob_cursor.execute("select * from %s.user limit 1" % database, exc_level='verbose'):
                        if not ob_cursor.execute("update %s.user set need_change_password=true where id='100'" % database, exc_level='verbose'):
                            stdio.verbose("failed to update 'need_change_password' to true in user table")
                            continue
                break
            except:
                if tenant_map.get(jdbc_username, {}):
                    database = tenant_map.get(jdbc_username, {}).get('database')
                    jdbc_username = tenant_map.get(jdbc_username, {}).get('user')
                time.sleep(1)
    if not connected:
        success = False
        stdio.warn("{}: failed to connect meta db".format(server))
    plugin_context.set_variable('cursor', ob_cursor)
    plugin_context.set_variable('database', database)
    plugin_context.set_variable('success', success)
    plugin_context.set_variable('jdbc_url', jdbc_url)
    return plugin_context.return_true()