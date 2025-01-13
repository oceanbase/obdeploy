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

import const
from tool import Cursor


def target_ob_connect_check(plugin_context, ob_deploy,  ob_cluster_repositories, proxy_deploy=None, retry_times=11, *args, **kwargs):

    ob_repository = None
    proxy_repository = None
    for repository in ob_cluster_repositories:
        if repository.name in const.COMPS_OB:
            ob_repository = repository
        elif repository.name in const.COMPS_ODP:
            proxy_repository = repository
    ob_cluster_config = ob_deploy.deploy_config.components[ob_repository.name]
    proxy_server = None
    proxy_server_config = None
    if proxy_deploy:
        proxy_cluster_config = proxy_deploy.deploy_config.components[proxy_repository.name]
        proxy_server = proxy_cluster_config.servers[0]
        proxy_server_config = proxy_cluster_config.get_server_conf(proxy_server)

    ob_server = ob_cluster_config.servers[0]
    ob_server_config = ob_cluster_config.get_server_conf(ob_server)

    stdio = plugin_context.stdio
    count = retry_times
    stdio.start_loading(f"Connect to observer{' and proxy'  if proxy_deploy else ''}")
    ob_cursor_success = False
    proxy_cursor_success = False if proxy_deploy else True
    proxy_cursor = None
    ob_cursor = None
    while count:
        count -= 1
        try:
            if proxy_deploy:
                port = proxy_server_config['listen_port']
                ip = proxy_server.ip
            else:
                port = ob_server_config['mysql_port']
                ip = ob_server.ip
            if not ob_cursor_success:
                ob_password = ob_cluster_config.get_server_conf(ob_server).get('root_password')
                cursor = Cursor(ip=ip, port=port, tenant='', password=ob_password, stdio=stdio)
                if cursor.execute('show databases;', raise_exception=False, exc_level='verbose'):
                    ob_cursor = cursor
                    stdio.verbose('connect to observer success')
                    ob_cursor_success = True
            if not proxy_cursor_success:
                proxy_password = proxy_server_config.get('obproxy_sys_password', '')
                proxy_cursor = Cursor(ip=proxy_server.ip, port=proxy_server_config['listen_port'], user='root@proxysys', tenant='',password=proxy_password, stdio=stdio)
                proxy_cursor_success = True
            if ob_cursor_success and proxy_cursor_success:
                stdio.stop_loading('succeed', text='Connect to observer {}:{}'.format(ob_server.ip, port))
                return plugin_context.return_true(ob_cursor=ob_cursor, proxy_cursor=proxy_cursor)
        except:
            if count == 0:
                stdio.exception('')
        time.sleep(3)

    stdio.stop_loading('fail')
    stdio.error(f"connect to observer{' by %s' % proxy_repository.name if proxy_deploy else ''} failed. ")
    return plugin_context.return_false()




