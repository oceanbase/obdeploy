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

import shlex
import time

from oblogservice_util import (
    build_global_option,
    find_running_pid,
    get_local_ip,
    is_oblogservice_running_with_config,
    pid_path,
)


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('start oblogservice')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        client = clients[server]
        local_ip = get_local_ip(server, server_config)
        rpc_port = int(server_config['port'])
        remote_pid_path = pid_path(home_path, local_ip, rpc_port)
        expected_option = build_global_option(cluster_config, server, server_config)

        if is_oblogservice_running_with_config(
                client, home_path, rpc_port, expected_option):
            running_pid = find_running_pid(client, home_path, rpc_port)
            stdio.verbose('%s oblogservice is already running with current config, skip start' % server)
            if running_pid:
                client.execute_command('echo "%s" > %s' % (running_pid, remote_pid_path))
            continue

        running_pid = find_running_pid(client, home_path, rpc_port)
        if running_pid:
            stdio.verbose('%s oblogservice config changed, restart process' % server)
            client.execute_command('kill -9 %s' % running_pid)
            time.sleep(1)

        global_opt = expected_option
        cmd = (
            "cd {home} && nohup {home}/bin/oblogservice -g {opt} "
            ">> {home}/log/oblogservice.log 2>&1 &"
        ).format(home=shlex.quote(home_path), opt=shlex.quote(global_opt))
        if not client.execute_command(cmd):
            stdio.stop_loading('fail')
            stdio.error('failed to start oblogservice on %s' % server)
            return plugin_context.return_false()

        for _ in range(30):
            time.sleep(1)
            running_pid = find_running_pid(client, home_path, rpc_port)
            if running_pid:
                client.execute_command('echo "%s" > %s' % (running_pid, remote_pid_path))
                break
        else:
            stdio.stop_loading('fail')
            stdio.error('failed to start oblogservice on %s' % server)
            return plugin_context.return_false()

        time.sleep(2)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
