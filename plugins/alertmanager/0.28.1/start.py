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
import time

def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    pid_path = {}
    cmd_args_map = plugin_context.get_variable('cmd_args_map')
    servers_pid = {}

    stdio.start_loading('Start alertmanager')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        bin_path = os.path.join(server_config["home_path"], 'alertmanager')
        log_path = os.path.join(server_config.get("log_dir", os.path.join(home_path, 'log')), "alertmanager.log")
        pid_path = os.path.join(home_path, 'run/alertmanager.pid')

        remote_pid_path = os.path.join(home_path, 'run/alertmanager.pid')
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            servers_pid[server] = remote_pid
            continue
        
        cmd_items = cmd_args_map.get(server)
        cmd_args = ' '.join(cmd_items)
        execute_cmd = '%s %s > %s 2>&1 &' % (bin_path, cmd_args, log_path)
        ret = client.execute_command(execute_cmd)
        if not ret:
            stdio.stop_loading('fail')
            stdio.error('failed to start %s alertmanager: %s' % (server, ret.stderr))
            return plugin_context.return_false()
        
        servers_pid[server] = None
        count = 10
        while count:
            count -= 1
            ret = client.execute_command('''ps -aux | grep -e '%s$' | grep -v grep | awk '{print $2}' ''' % f"{bin_path} {cmd_args}")
            if ret and ret.stdout.strip():
                servers_pid[server] = ret.stdout.strip()
                break
            time.sleep(1)
        
        if not servers_pid[server]:
            stdio.error("failed to start {} alertmanager after 10 seconds".format(server))
            return plugin_context.return_false()
        client.write_file(servers_pid[server], os.path.join(home_path, pid_path))

    stdio.stop_loading('succeed')
    plugin_context.set_variable('servers_pid', servers_pid)    
    return plugin_context.return_true()


