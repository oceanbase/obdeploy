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

import const
from _rpm import Version
from tool import ConfigUtil, NetUtil


def proxy_register_binlog(plugin_context, proxy_version, *args, **kwargs):
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('target_ob_connect_check').get_return('proxy_cursor')
    if not cursor:
        stdio.error("tenant_check plugin need proxy_cursor")
        return plugin_context.return_false()
    clients = plugin_context.clients

    cluster_config = plugin_context.cluster_config
    ips = ''
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        ip = NetUtil.get_host_ip() if client.is_localhost() else server.ip
        if not ips:
            ips += ip + ":" + str(server_config.get('service_port'))
            if len(cluster_config.servers) > 1 and proxy_version < Version('4.3.1'):
                stdio.warn(f"Register only one binlog server(%s) to obproxy. If you need to register all IPs, please use obproxy version greater than 4.3.1." % (str(server.ip)))
                break
        else:
            ips += ';' + ip + ":" + str(server_config.get('service_port'))
    try:
        cursor.execute(f"alter proxyconfig set binlog_service_ip='{ips}'", raise_exception=True)
        if proxy_version < Version('4.2.3'):
            cursor.execute("ALTER proxyconfig SET enable_binlog_service='True'", raise_exception=True)
    except Exception as e:
        stdio.error(e)
        return plugin_context.return_false()
    return plugin_context.return_true()

