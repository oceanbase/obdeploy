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

import time

from _errno import EC_OBSERVER_FAIL_TO_START


def health_check(plugin_context, *args, **kwargs):
    if plugin_context.get_variable('scale_out'):
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('observer program health check')
    time.sleep(3)
    failed = []
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/observer.pid' % home_path
        stdio.verbose('%s program health check' % server)
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid and client.execute_command('ls /proc/%s' % remote_pid):
            stdio.verbose('%s observer[pid: %s] started', server, remote_pid)
        else:
            failed.append(EC_OBSERVER_FAIL_TO_START.format(server=server))
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        return plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')

    restart_manager = plugin_context.get_variable('restart_manager')
    if restart_manager:
        restart_manager.close()

    return plugin_context.return_true()
