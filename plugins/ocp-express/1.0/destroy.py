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

import re
from copy import deepcopy

import _errno as err

global_ret = True


def check_mount_path(client, path, stdio):
    stdio and getattr(stdio, 'verbose', print)('check mount: %s' % path)
    try:
        if client.execute_command("grep '\\s%s\\s' /proc/mounts" % path):
            return True
        return False
    except Exception as e:
        stdio and getattr(stdio, 'exception', print)('')
        stdio and getattr(stdio, 'error', print)('failed to check mount: %s' % path)


def get_missing_required_parameters(parameters):
    results = []
    for key in ["jdbc_url", "jdbc_password", "jdbc_username"]:
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
                "ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password"
            ]
            for key in ocp_meta_keys:
                value = observer_globals.get(key)
                if value is not None:
                    depend_info[key] = value
            ob_servers = cluster_config.get_depend_servers(comp)

            connect_infos = []
            for ob_server in ob_servers:
                ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                connect_infos.append([ob_server.ip, ob_server_conf['mysql_port']])
                zone = ob_server_conf['zone']
                if zone not in ob_zones:
                    ob_zones[zone] = ob_server
            depend_info['connect_infos'] = connect_infos
            root_servers = ob_zones.values()
            break
        
    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        original_server_config = cluster_config.get_original_server_conf(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                    server_config['connect_infos'] = depend_info.get('connect_infos')
                    server_config['ocp_meta_db'] = depend_info.get('ocp_meta_db')
            if 'jdbc_username' in missed_keys and depend_observer:
                server_config['jdbc_username'] = "{}@{}".format(depend_info['ocp_meta_username'],
                    depend_info.get('ocp_meta_tenant', {}).get("tenant_name"))
            if 'jdbc_password' in missed_keys and depend_observer:
                server_config['jdbc_password'] = depend_info['ocp_meta_password']
        env[server] = server_config
    return env


def destroy(plugin_context, *args, **kwargs):
    def clean_database(cursor, database):
        ret = cursor.execute("drop database {0}".format(database))
        if not ret:
            global global_ret
            global_ret = False
        cursor.execute("create database if not exists {0}".format(database))

    def clean(path):
        client = clients[server]
        if check_mount_path(client, path, stdio):
            ret = client.execute_command('rm -fr %s/*' % path, timeout=-1)
        else:
            ret = client.execute_command('rm -fr %s' % path, timeout=-1)
        if not ret:
            global global_ret
            global_ret = False
            stdio.warn(err.EC_CLEAN_PATH_FAILED.format(server=server, path=path))
        else:
            stdio.verbose('%s:%s cleaned' % (server, path))

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global global_ret

    removed_components = cluster_config.get_deploy_removed_components()
    clean_data = (not cluster_config.depends or len(removed_components) > 0 and len(removed_components.intersection({"oceanbase", "oceanbase-ce"})) == 0) and stdio.confirm("Would you like to clean meta data")

    stdio.start_loading('ocp-express cleaning')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s work path cleaning', server)
        home_path = server_config['home_path']
        clean(home_path)
        log_dir = server_config.get('log_dir')
        if log_dir:
            clean(log_dir)

    if clean_data:
        stdio.verbose("clean metadb")
        env = prepare_parameters(cluster_config, stdio)
        for server in cluster_config.servers:
            server_config = env[server]
            jdbc_host, jdbc_port = "", 0
            if 'jdbc_url' in server_config:
                matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", server_config['jdbc_url'])
                if matched:
                    jdbc_host = matched.group(1)
                    jdbc_port = matched.group(2)[1:]
                    connect_infos = [[jdbc_host, jdbc_port]]            
                    database = matched.group(3)
                else:
                    stdio.error("failed to parse jdbc_url")
            else:
                connect_infos = server_config.get('connect_infos', '')
                database = server_config.get('ocp_meta_db', '')     

            connected = False
            for connect_info in connect_infos:
                try:
                    meta_cursor = Cursor(connect_info[0], connect_info[1], user=server_config['jdbc_username'], password=server_config['jdbc_password'], stdio=stdio)
                    connected = True
                    break
                except:
                    continue
            if connected: 
                try:
                    clean_database(meta_cursor, database)
                except Exception:
                    stdio.error("failed to clean meta data")
                    global_ret = False
            else:
                stdio.error("failed to connect to ocp meta tenant")
                global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
