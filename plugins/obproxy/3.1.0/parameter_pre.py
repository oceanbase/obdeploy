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

from tool import NetUtil


def parameter_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    obproxy_config_server_url = ''

    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            root_servers = {}
            ob_config = cluster_config.get_depend_config(comp)
            if not ob_config:
                continue
            odp_config = cluster_config.get_global_conf()
            for server in cluster_config.get_depend_servers(comp):
                config = cluster_config.get_depend_config(comp, server)
                zone = config['zone']
                if zone not in root_servers:
                    root_servers[zone] = '%s:%s' % (server.ip, config['mysql_port'])
            depend_rs_list = ';'.join([root_servers[zone] for zone in root_servers])
            cluster_config.update_global_conf('rs_list', depend_rs_list, save=False)

            config_map = {
                'cluster_name': 'appname'
            }
            for key in config_map:
                ob_key = config_map[key]
                if key not in odp_config and ob_key in ob_config:
                    cluster_config.update_global_conf(key, ob_config.get(ob_key), save=False)
            break

    obc_cluster_config = cluster_config.get_depend_config('ob-configserver')
    if obc_cluster_config:
        vip_address = obc_cluster_config.get('vip_address')
        if vip_address:
            obc_ip = vip_address
            obc_port = obc_cluster_config.get('vip_port')
        else:
            server = cluster_config.get_depend_servers('ob-configserver')[0]
            client = clients[server]
            obc_ip = NetUtil.get_host_ip() if client.is_localhost() else server.ip
            obc_port = obc_cluster_config.get('listen_port')
        obproxy_config_server_url = "http://{0}:{1}/services?Action=GetObProxyConfig".format(obc_ip, obc_port)
    plugin_context.set_variable('obproxy_config_server_url', obproxy_config_server_url)

    error = False
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        if 'rs_list' not in server_config and 'obproxy_config_server_url' not in server_config and not obproxy_config_server_url:
            error = True
            stdio.error('%s need config "rs_list" or "obproxy_config_server_url"' % server)
    if error:
        return plugin_context.return_false()

    plugin_context.return_true()
