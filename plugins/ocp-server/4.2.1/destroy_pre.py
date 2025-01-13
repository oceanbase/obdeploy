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
from tool import Cursor

global_ret = True

def destroy_pre(plugin_context, *args, **kwargs):
    def clean_database(cursor, database):
        ret = cursor.execute("drop database {0}".format(database))
        if not ret:
            global global_ret
            global_ret = False
        cursor.execute("create database if not exists {0}".format(database))

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global global_ret
    removed_components = cluster_config.get_deploy_removed_components()
    clean_data = (not cluster_config.depends or len(removed_components) > 0 and len(removed_components.intersection({"oceanbase", "oceanbase-ce"})) == 0) and stdio.confirm("Would you like to clean meta data")

    plugin_context.set_variable("clean_dirs", ['log_dir', 'soft_dir'])
    sudo_command = {}
    clients = plugin_context.clients
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        if not client.execute_command('[ `id -u` == "0" ]') and server_config.get('launch_user', '') and client.execute_command('sudo -n true'):
            sudo_command[server] = "sudo "
    if sudo_command:
        plugin_context.set_variable("sudo_command", sudo_command)

    
    if clean_data:
        stdio.start_loading('ocp-server metadb and monitordb cleaning')
        env = plugin_context.get_variable('start_env')
        jdbc_url = env[cluster_config.servers[0]]['jdbc_url']
        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
        host = matched.group(1)
        port = matched.group(2)[1:]
        if not env:
            return plugin_context.return_true()
        
        server_config = env[cluster_config.servers[0]]
        stdio.verbose("clean metadb")
        try:
            meta_cursor = Cursor(host, port, user=server_config['ocp_meta_username'], tenant=server_config['ocp_meta_tenant']['tenant_name'], password=server_config['ocp_meta_password'], stdio=stdio)
            clean_database(meta_cursor, server_config['ocp_meta_db'])
            stdio.verbose("clean monitordb")
            monitor_cursor = Cursor(host, port, user=server_config['ocp_monitor_username'], tenant=server_config['ocp_monitor_tenant']['tenant_name'], password=server_config['ocp_monitor_password'], stdio=stdio)
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