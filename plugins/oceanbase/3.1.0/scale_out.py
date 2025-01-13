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


def scale_out(plugin_context, cursor=None, *args, **kwargs):
    if not cursor:
        raise Exception('Cursor could not be None')
    def error(msg='', *arg, **kwargs):
        msg and stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('fail')
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value
    
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    stdio.start_loading('scaling out')
    server_configs = {}
    for server in cluster_config.added_servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        server_configs[server]=server_config
        zone = server_config.get('zone')
        zone_region = server_config.get('region')
        ret = cursor.fetchone('select * from oceanbase.__all_zone where zone = %s', zone)
        if ret is False:
            error("Failed to search zone %s", zone)
            return False
        if not ret:
            if not zone_region:
                ret = cursor.fetchone('select * from oceanbase.__all_zone where name = "region" limit 1')
                if ret:
                    zone_region = ret.get('info')
            # add new zone
            if not cursor.execute('alter system add zone %s region %s '%(zone, zone_region)):
                error("Failed to add zone %s", zone)
                return False
            if not cursor.execute('alter system start zone %s', zone):
                error("Failed to start zone %s", zone)
                return False
        else:
            stdio.verbose("Zone %s already exists", zone)
        ret = cursor.fetchone("select * from oceanbase.__all_server where svr_ip=%s and inner_port=%s", (server.ip, server_config['mysql_port']))
        if ret:
            stdio.verbose("Server '%s:%s' already exists", server.ip, server_config['mysql_port'])
            continue
        # add new observer
        if cursor.execute("alter system add server '%s:%s' zone %s"%(server.ip, server_config['rpc_port'], zone)) is False:
            error("Failed to add server '%s:%s'"%(server.ip, server_config['rpc_port']))
            return False
    stdio.stop_loading('succeed')

    stdio.start_loading("Waiting for observers ready")
    timeout = get_option('scale_out_timeout', 3600)
    for i in range(timeout):
        observers = cursor.fetchall("select svr_ip, inner_port from oceanbase.__all_server where status = 'active' and start_service_time is not NULL")
        for server in cluster_config.added_servers:
            if any([observer['svr_ip'] == server.ip and observer['inner_port'] == server_configs[server]['mysql_port'] for observer in observers]):
                continue
            else:
                # 存在非active的observer
                break
        else:
            # 说明所有节点都是active的
            break
        time.sleep(1)
    else:
        # 说明超时了
        stdio.stop_loading('warn')
        return plugin_context.return_true()
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()

