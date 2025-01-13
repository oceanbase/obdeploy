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

def destroy_pre(plugin_context, *args, **kwargs):
    def stop_converter():
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            home_path = server_config['home_path']
            binlog_dir = server_config.get('binlog_dir') if server_config.get('binlog_dir') else '{}/run'.format(home_path)
            ret = client.execute_command("ps -aux | grep './binlog_converter' | grep '%s' | grep -v grep | awk '{print $2}'" % binlog_dir)
            if ret and ret.stdout:
                pids = ret.stdout.strip().split('\n')
                for pid in pids:
                    if client.execute_command('ls /proc/%s/fd' % pid):
                        stdio.verbose('%s binlog_converter[pid:%s] stopping ...' % (server, pid))
                        client.execute_command('kill -9 %s' % pid)

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('oblogproxy stop binlog_converter')
    stop_converter()
    stdio.stop_loading('succeed')

    plugin_context.set_variable("clean_dirs", ["binlog_dir"])

    return plugin_context.return_true()