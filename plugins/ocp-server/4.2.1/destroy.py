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
import _errno as err
from tool import Cursor

global_ret = True


def destroy(plugin_context, *args, **kwargs):

    def clean_database(cursor, database):
        ret = cursor.execute("drop database {0}".format(database))
        if not ret:
            global global_ret
            global_ret = False
        cursor.execute("create database if not exists {0}".format(database))

    def clean(path):
        client = clients[server]
        ret = client.execute_command('sudo rm -fr %s/*' % path, timeout=-1)
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
        jdbc_host, jdbc_port = "", 0
        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", cluster_config.get_global_conf_with_default()['jdbc_url'])
        if matched:
            jdbc_host = matched.group(1)
            jdbc_port = matched.group(2)[1:]
        else:
            stdio.error("failed to parse jdbc_url")
        global_conf = cluster_config.get_global_conf_with_default()
        stdio.verbose("clean metadb")
        try:
            meta_cursor = Cursor(jdbc_host, jdbc_port, user=global_conf['ocp_meta_username'], tenant=global_conf['ocp_meta_tenant']['tenant_name'], password=global_conf['ocp_meta_password'], stdio=stdio)
            clean_database(meta_cursor, global_conf['ocp_meta_db'])
            stdio.verbose("clean monitordb")
            monitor_cursor = Cursor(jdbc_host, jdbc_port, user=global_conf['ocp_monitor_username'], tenant=global_conf['ocp_monitor_tenant']['tenant_name'], password=global_conf['ocp_monitor_password'], stdio=stdio)
            clean_database(monitor_cursor, global_conf['ocp_monitor_db'])
        except Exception:
            stdio.error("failed to clean meta and monitor data")
            global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
