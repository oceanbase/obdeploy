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
from tool import Cursor

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
    for key in ["jdbc_url"]:
        if parameters.get(key) is None:
            results.append(key)
    return results


def get_ocp_depend_config(cluster_config, stdio):
    # depends config
    env = {}
    depend_observer = False
    depend_info = {}
    ob_servers_conf = {}
    for comp in ["oceanbase", "oceanbase-ce"]:
        ob_zones = {}
        if comp in cluster_config.depends:
            depend_observer = True
            ob_servers = cluster_config.get_depend_servers(comp)
            for ob_server in ob_servers:
                ob_servers_conf[ob_server] = ob_server_conf = cluster_config.get_depend_config(comp, ob_server)
                if 'server_ip' not in depend_info:
                    depend_info['server_ip'] = ob_server.ip
                    depend_info['mysql_port'] = ob_server_conf['mysql_port']
                    depend_info['meta_tenant'] = ob_server_conf['ocp_meta_tenant']['tenant_name']
                    depend_info['meta_user'] = ob_server_conf['ocp_meta_username']
                    depend_info['meta_password'] = ob_server_conf['ocp_meta_password']
                    depend_info['meta_db'] = ob_server_conf['ocp_meta_db']
                    depend_info['monitor_tenant'] = ob_server_conf['ocp_monitor_tenant']['tenant_name']
                    depend_info['monitor_user'] = ob_server_conf['ocp_monitor_username']
                    depend_info['monitor_password'] = ob_server_conf['ocp_monitor_password']
                    depend_info['monitor_db'] = ob_server_conf['ocp_monitor_db']
                zone = ob_server_conf['zone']
                if zone not in ob_zones:
                    ob_zones[zone] = ob_server
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
        default_server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        server_config = deepcopy(cluster_config.get_server_conf(server))
        original_server_config = cluster_config.get_original_server_conf_with_global(server)
        missed_keys = get_missing_required_parameters(original_server_config)
        if missed_keys:
            if 'jdbc_url' in missed_keys and depend_observer:
                default_server_config['jdbc_url'] = 'jdbc:oceanbase://{}:{}/{}'.format(depend_info['server_ip'], depend_info['mysql_port'], depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']) if not original_server_config.get('jdbc_url', None) else original_server_config['jdbc_url']
                default_server_config['ocp_meta_username'] = depend_info['meta_user'] if not original_server_config.get('ocp_meta_username', None) else original_server_config['ocp_meta_username']
                default_server_config['ocp_meta_tenant']['tenant_name'] = depend_info['meta_tenant'] if not original_server_config.get('ocp_meta_tenant', None) else original_server_config['ocp_meta_tenant']['tenant_name']
                default_server_config['ocp_meta_password'] = depend_info['meta_password'] if not original_server_config.get('ocp_meta_password', None) else original_server_config['ocp_meta_password']
                default_server_config['ocp_meta_db'] = depend_info['meta_db'] if not original_server_config.get('ocp_meta_db', None) else original_server_config['ocp_meta_db']
                default_server_config['ocp_monitor_username'] = depend_info['monitor_user'] if not original_server_config.get('ocp_monitor_username', None) else original_server_config['ocp_monitor_username']
                default_server_config['ocp_monitor_tenant']['tenant_name'] = depend_info['monitor_tenant'] if not original_server_config.get('ocp_monitor_tenant', None) else original_server_config['ocp_monitor_tenant']['tenant_name']
                default_server_config['ocp_monitor_password'] = depend_info['monitor_password'] if not original_server_config.get('ocp_monitor_password', None) else original_server_config['ocp_monitor_password']
                default_server_config['ocp_monitor_db'] = depend_info['monitor_db'] if not original_server_config.get('ocp_monitor_db', None) else original_server_config['ocp_monitor_db']
        env[server] = default_server_config
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
        cmd = 'rm -fr %s/' % path
        if check_mount_path(client, path, stdio):
            cmd = 'rm -fr %s/*' % path
        if not client.execute_command('[ `id -u` == "0" ]') and server_config.get('launch_user', '') and client.execute_command('sudo -n true'):
            cmd = 'sudo' + cmd
        ret = client.execute_command(cmd, timeout=-1)
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
    
    stdio.start_loading('ocp-server cleaning')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s work path cleaning', server)
        home_path = server_config['home_path']
        clean(home_path)

        for key in ['log_dir', 'soft_dir']:
            path = server_config.get(key)
            if path:
                clean(path)

    if clean_data:
        env = get_ocp_depend_config(cluster_config, stdio)
        if not env:
            return plugin_context.return_true()

        server_config = env[cluster_config.servers[0]]

        jdbc_host, jdbc_port = "", 0
        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", server_config['jdbc_url'])
        if matched:
            jdbc_host = matched.group(1)
            jdbc_port = matched.group(2)[1:]
        else:
            stdio.error("failed to parse jdbc_url")
        stdio.verbose("clean metadb")
        try:
            meta_cursor = Cursor(jdbc_host, jdbc_port, user=server_config['ocp_meta_username'], tenant=server_config['ocp_meta_tenant']['tenant_name'], password=server_config['ocp_meta_password'], stdio=stdio)
            clean_database(meta_cursor, server_config['ocp_meta_db'])
            stdio.verbose("clean monitordb")
            monitor_cursor = Cursor(jdbc_host, jdbc_port, user=server_config['ocp_monitor_username'], tenant=server_config['ocp_monitor_tenant']['tenant_name'], password=server_config['ocp_monitor_password'], stdio=stdio)
            clean_database(monitor_cursor, server_config['ocp_monitor_db'])
        except Exception:
            stdio.error("failed to clean meta and monitor data")
            global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
