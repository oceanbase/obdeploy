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

from oblogservice_util import get_local_ip, pid_path


def destroy_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('stop oblogservice before destroy')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        local_ip = get_local_ip(server, server_config)
        port = int(server_config['port'])
        remote_pid_path = pid_path(home_path, local_ip, port)
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            client.execute_command('kill -9 %s' % remote_pid)
        ret = client.execute_command(
            "ps -aux | grep '%s/bin/oblogservice -g' | grep -v grep | awk '{print $2}'" % home_path
        )
        if ret and ret.stdout and ret.stdout.strip():
            for pid in ret.stdout.strip().split('\n'):
                client.execute_command('kill -9 %s' % pid)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
