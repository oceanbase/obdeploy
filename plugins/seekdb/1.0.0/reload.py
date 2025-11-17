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

from urllib.parse import urlparse

import requests

from _deploy import InnerConfigItem
from _errno import EC_OBSERVER_INVALID_MODFILY_GLOBAL_KEY
from ssh import get_root_permission_client
from tool import is_root_user
from _errno import EC_OBSERVER_DISABLE_AUTOSTART
from collections import Counter
import os


def get_ob_configserver_cfg_url(obconfig_url, appname, stdio):
    parsed_url = urlparse(obconfig_url)
    host = parsed_url.netloc
    stdio.verbose('obconfig_url host: %s' % host)
    url = '%s://%s/debug/pprof/cmdline' % (parsed_url.scheme, host)
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code != 200:
            stdio.verbose('request %s status_code: %s' % (url, str(response.status_code)))
            return None
    except Exception:
        stdio.verbose('Configserver url check failed: request %s failed' % url)
        return None

    if obconfig_url[-1] == '?':
        link_char = ''
    elif obconfig_url.find('?') == -1:
        link_char = '?'
    else:
        link_char = '&'
    cfg_url = '%s%sAction=ObRootServiceInfo&ObCluster=%s' % (obconfig_url, link_char, appname)
    return cfg_url

def contains_duplicate_nodes(servers):
    ips = [server.ip for server in servers]
    ip_counter = Counter(ips)
    duplicates = {ip: count for ip, count in ip_counter.items() if count > 1}
    return duplicates


def reload(plugin_context, new_cluster_config, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    cursor = plugin_context.get_return('connect').get_return('cursor')
    cursor = cursor.usable_cursor
    cursor.execute('set session ob_query_timeout=1000000000')

    not_paramters = ['production_mode', 'local_ip', 'obshell_port']
    cluster_server = {}
    change_conf = {}
    global_change_conf = {}
    global_ret = True
    need_restart_key = []
    for server in servers:
        change_conf[server] = {}
        stdio.verbose('get %s old configuration' % (server))
        config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s new configuration' % (server))
        new_config = new_cluster_config.get_server_conf_with_default(server)
        stdio.verbose('compare configuration of %s' % (server))
        for key in new_config:
            if key in not_paramters:
                stdio.verbose('%s is not a oceanbase parameter. skip' % key)
                continue
            n_value = new_config[key]
            if key == 'obconfig_url':
                cfg_url = get_ob_configserver_cfg_url(n_value, cluster_config.name, stdio)
                if cfg_url:
                    n_value = cfg_url
            if key == 'data_dir' and not config.get(key) and n_value =='%s/store' % config['home_path']:
                continue
            if key not in config or config[key] != n_value:
                item = cluster_config.get_temp_conf_item(key)
                if item:
                    if item.need_restart:
                        need_restart_key.append(key)
                        stdio.verbose('%s can not be reload' % key)
                        if not plugin_context.get_return("restart_pre"):
                            global_ret = False
                            continue
                    if item.need_redeploy:
                        stdio.verbose('%s can not be reload' % key)
                        global_ret = False
                        continue
                    try:
                        item.modify_limit(config.get(key), n_value)
                    except Exception as e:
                        global_ret = False
                        stdio.verbose('%s: %s' % (server, str(e)))
                        continue
                change_conf[server][key] = n_value
                if key not in global_change_conf:
                    global_change_conf[key] = {'value': n_value, 'count': 1}
                elif n_value == global_change_conf[key]['value']:
                    global_change_conf[key]['count'] += 1

    servers_num = len(servers)
    auto_start_clients = {}
    if global_change_conf.get('enable_auto_start') and global_change_conf['enable_auto_start']['value'] == False:
        clients = plugin_context.clients
        if contains_duplicate_nodes(cluster_config.servers):
            stdio.error("The auto start of multiple nodes is not supported. Please modify the node configuration.")
            return plugin_context.return_false()
        for server in cluster_config.servers:
            client = clients[server]
            auto_start_client = get_root_permission_client(client, server, stdio)
            if not auto_start_client:
                return plugin_context.return_false()
            if not client.execute_command("systemctl status dbus"):
                stdio.error("%s does not support the systemctl command, so the observer cannot be set to start automatically." % server)
                return plugin_context.return_false()
            auto_start_clients[server] = auto_start_client
    
    if global_change_conf.get('install_utils'):
        if global_change_conf['install_utils']['value'] == False:
            stdio.warn("Uninstalling oceanbase-ce-utils is not currently supported")
        else:
            server_config = cluster_config.get_server_conf(cluster_config.servers[0])
            utils_flag = os.path.join(server_config['home_path'], 'bin', 'ob_admin')
            client = plugin_context.clients[cluster_config.servers[0]]
            cmd = 'ls %s' % utils_flag
            if not client.execute_command(cmd):
                install_utils_to_servers = kwargs.get("install_utils_to_servers")
                get_repositories_utils = kwargs.get("get_repositories_utils")
                repositories = plugin_context.repositories
                repositories_utils_map = get_repositories_utils(repositories)
                ret = install_utils_to_servers(repositories, repositories_utils_map)
                if not ret:
                    return plugin_context.return_false()
    
    stdio.verbose('apply new configuration')
    stdio.start_loading('Reload observer')
    raise_cursor = cursor.raise_cursor
    for key in global_change_conf:
        try:
            if key in set(need_restart_key):
                continue
            if key in ['proxyro_password', 'root_password']:
                if global_change_conf[key]['count'] != servers_num:
                    stdio.warn(EC_OBSERVER_INVALID_MODFILY_GLOBAL_KEY.format(key=key))
                    continue
                value = change_conf[server][key] if change_conf[server].get(key) is not None else ''
                user = key.split('_')[0]
                sql = 'CREATE USER IF NOT EXISTS %s IDENTIFIED BY %%s' % (user)
                raise_cursor.execute(sql, [value])
                sql = 'alter user "%s" IDENTIFIED BY %%s' % (user)
                raise_cursor.execute(sql, [value])
                continue
            if key == 'enable_auto_start':
                if global_change_conf[key]['value'] == False:
                    server_config = cluster_config.get_server_conf(server)
                    for server in cluster_config.servers:
                        auto_start_client = auto_start_clients[server]
                        global_config = cluster_config.get_global_conf()
                        appname = global_config['appname']
                        observer_service = 'obd_oceanbase_%s.service' % appname
                        disable_auto_start_cmd = "systemctl disable"
                        if not is_root_user(auto_start_client):
                            disable_auto_start_cmd = f"echo {auto_start_client.config.password} | sudo -S {disable_auto_start_cmd}"
                        if not auto_start_client.execute_command('%s %s' % (disable_auto_start_cmd, observer_service)):
                            stdio.error(EC_OBSERVER_DISABLE_AUTOSTART.format(server=server))
                            return plugin_context.return_false()
                        auto_start_flag = os.path.join(server_config['home_path'], '.enable_auto_start')
                        if not auto_start_client.execute_command('rm -f %s' % auto_start_flag):
                            stdio.warn('remove %s is failed' % auto_start_flag)
                continue
            
            if key == 'install_utils':
                continue
                
            if global_change_conf[key]['count'] == servers_num:
                sql = 'alter system set %s = %%s' % key
                value = change_conf[server][key]
                raise_cursor.execute(sql, [value])
                cluster_config.update_global_conf(key, value, False)
                continue
            for server in servers:
                if key not in change_conf[server]:
                    continue
                value = change_conf[server][key]
                sql = 'alter system set %s = %%s server=%%s' % key
                raise_cursor.execute(sql, [value, cluster_server[server]])
                cluster_config.update_server_conf(server, key, value, False)
        except:
            stdio.exception("")
            global_ret = False

    try:
        raise_cursor.execute('alter system reload server')
        raise_cursor.execute('alter system reload unit')
    except:
        stdio.exception("")
        global_ret = False
    
    if global_ret:
        plugin_context.set_variable("change_conf", change_conf)
        plugin_context.set_variable("global_change_conf", global_change_conf)
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return
