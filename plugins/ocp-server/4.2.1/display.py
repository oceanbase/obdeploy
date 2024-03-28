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

from tool import NetUtil
from copy import deepcopy


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username", "cluster_name", "ob_cluster_id", "root_sys_password",
                "server_addresses", "agent_username", "agent_password"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def prepare_parameters(cluster_config, stdio):
    # depends config
    env = {}
    depend_observer = False
    depend_info = {}
    ob_servers_conf = {}
    root_servers = []
    for comp in ["oceanbase", "oceanbase-ce"]:
        ob_zones = {}
        if comp in cluster_config.depends:
            depend_observer = True
            observer_globals = cluster_config.get_depend_config(comp)
            ocp_meta_keys = [
                "ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password", "appname", "cluster_id", "root_password"
            ]
            for key in ocp_meta_keys:
                value = observer_globals.get(key)
                if value is not None:
                    depend_info[key] = value
            ob_servers = cluster_config.get_depend_servers(comp)
            for ob_server in ob_servers:
                ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                if 'server_ip' not in depend_info:
                    depend_info['server_ip'] = ob_server.ip
                    depend_info['mysql_port'] = ob_server_conf['mysql_port']
                zone = ob_server_conf['zone']
                if zone not in ob_zones:
                    ob_zones[zone] = ob_server
            root_servers = ob_zones.values()
            break
    for comp in ['obproxy', 'obproxy-ce']:
        if comp in cluster_config.depends:
            obproxy_servers = cluster_config.get_depend_servers(comp)
            obproxy_server = obproxy_servers[0]
            obproxy_server_config = cluster_config.get_depend_config(comp, obproxy_server)
            depend_info['server_ip'] = obproxy_server.ip
            depend_info['mysql_port'] = obproxy_server_config['listen_port']
            break

    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['ocp_meta_db'])
            if 'jdbc_username' in missed_keys and depend_observer:
                server_config['jdbc_username'] = "{}@{}".format(depend_info['ocp_meta_username'],
                    depend_info.get('ocp_meta_tenant', {}).get("tenant_name"))
            depends_key_maps = {
                "jdbc_password": "ocp_meta_password",
                "cluster_name": "appname",
                "ob_cluster_id": "cluster_id",
                "root_sys_password": "root_password",
                "agent_username": "obagent_username",
                "agent_password": "obagent_password",
                "server_addresses": "server_addresses"
            }
            for key in depends_key_maps:
                if key in missed_keys:
                    if depend_info.get(depends_key_maps[key]) is not None:
                        server_config[key] = depend_info[depends_key_maps[key]]
        env[server] = server_config
    return env


def display(plugin_context, cursor, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    servers = cluster_config.servers
    results = []
    start_env = prepare_parameters(cluster_config, stdio)
    for server in servers:
        api_cursor = cursor.get(server)
        server_config = start_env[server]
        ip = server.ip
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        url = 'http://{}:{}'.format(ip, api_cursor.port)
        results.append({
            'ip': ip,
            'port': api_cursor.port,
            'user': "admin",
            'password': server_config['admin_password'],
            'url': url,
            'status': 'active' if api_cursor and api_cursor.status(stdio) else 'inactive'
        })
    stdio.print_list(results, ['url', 'username', 'password', 'status'], lambda x: [x['url'], 'admin', server_config['admin_password'], x['status']], title='%s' % cluster_config.name)
    active_result = [r for r in results if r['status'] == 'active']
    info_dict = active_result[0] if len(active_result) > 0 else None
    if info_dict is not None:
        info_dict['type'] = 'web'
    return plugin_context.return_true(info=info_dict)
