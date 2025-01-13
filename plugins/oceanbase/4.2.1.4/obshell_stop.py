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


def obshell_stop(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('Stop obshell')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s obshell stopping ...' % (server))
        home_path = server_config['home_path']
        cmd = 'cd %s; %s/bin/obshell admin stop' % (home_path, home_path)
        if not client.execute_command(cmd):
            stdio.stop_loading('fail')
            return
        # check obshell is stopped
        remote_pid_path = '%s/run/obshell.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ps uax | egrep " %s " | grep -v grep' % remote_pid):
            stdio.stop_loading('fail')
            return
        remote_pid_path = '%s/run/daemon.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ps uax | egrep " %s " | grep -v grep' % remote_pid):
            stdio.stop_loading('fail')
            return

    stdio.stop_loading('succeed')

    plugin_context.return_true()