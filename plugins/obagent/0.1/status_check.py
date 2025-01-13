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


def status_check(plugin_context, precheck=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    running_status = {}
    
    for server in cluster_config.servers:
        running_status[server] = False
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        if not precheck:
            remote_pid_path = "%s/run/obagent-%s-%s.pid" % (server_config['home_path'], server.ip, server_config["server_port"])
            remote_pid = client.execute_command("cat %s" % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is runnning, skip' % server)
                    wait_2_pass(server)
                    running_status[server] = True
    plugin_context.set_variable('running_status', running_status)
    return plugin_context.return_true()