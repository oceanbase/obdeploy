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

import os
from ssh import get_root_permission_client
from tool import is_root_user
from collections import Counter

def contains_duplicate_nodes(servers):
    ips = [server.ip for server in servers]
    ip_counter = Counter(ips)
    duplicates = {ip: count for ip, count in ip_counter.items() if count > 1}
    return duplicates

def enable_auto_start(plugin_context, *args, **kwargs):
    new_cluster_config = kwargs.get('new_cluster_config')
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf()
    if new_cluster_config:
        old_config = cluster_config.get_server_conf_with_default(cluster_config.servers[0])
        new_config = new_cluster_config.get_server_conf_with_default(cluster_config.servers[0])
        enable_start_value = new_config['enable_auto_start']
        if enable_start_value == old_config['enable_auto_start'] or enable_start_value == False:
            return plugin_context.return_true()

    clients = plugin_context.clients
    stdio = plugin_context.stdio
    local_dir, _ = os.path.split(__file__)
    auto_path = os.path.join(local_dir, 'auto_start.sh')

    auto_start_clients = {}
    if contains_duplicate_nodes(cluster_config.servers):
        stdio.error("the auto start of multiple nodes is not supported. Please modify the node configuration.")
        return plugin_context.return_false()

    for server in cluster_config.servers:
        client = clients[server]
        auto_start_client = get_root_permission_client(client, server, stdio)
        if not auto_start_client:
            return plugin_context.return_false()
        ret = auto_start_client.execute_command("systemctl status dbus")
        if not ret:
            stdio.error(ret.stderr)
            return plugin_context.return_false()
        auto_start_clients[server] = auto_start_client

    stdio.start_loading('Setting observer to start automatically')
    for server in cluster_config.servers:
        auto_start_client = auto_start_clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        dst_path = os.path.join(home_path, 'auto_start.sh')
        client = clients[server]
        if not client.put_file(auto_path, dst_path, stdio=plugin_context.stdio):
            stdio.error("failed to put auto_start.sh {} to {}".format(auto_path, dst_path))
            return plugin_context.return_false()
        cmd = "sh %s %s %s" % (dst_path, home_path, global_config['appname'])
        if not is_root_user(auto_start_client):
            cmd = f"echo {auto_start_client.config.password} | sudo -S {cmd}"
        ret = auto_start_client.execute_command(cmd)
        if not ret:
            stdio.stop_loading('failed')
            stdio.verbose(ret.stdout)
            stdio.error(ret.stderr)
            return plugin_context.return_false()
        auto_start_flag = os.path.join(server_config['home_path'], '.enable_auto_start')
        client.execute_command('touch %s' % auto_start_flag)

    stdio.stop_loading('succeed')
    stdio.print('observer service: obd_oceanbase_%s.service' % global_config['appname'])
    return plugin_context.return_true()