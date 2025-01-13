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


def status(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    cluster_status = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        cluster_status[server] = 0
        pid_path = os.path.join(server_config['home_path'], 'run/ocp-express.pid')
        pids = client.execute_command('cat {}'.format(pid_path)).stdout.strip().split('\n')
        for pid in pids:
            if pid and client.execute_command('ls /proc/{}'.format(pid)):
                cluster_status[server] = 1
    return plugin_context.return_true(cluster_status=cluster_status)