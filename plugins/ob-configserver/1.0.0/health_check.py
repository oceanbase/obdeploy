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

from _errno import EC_OBC_PROGRAM_START_ERROR


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients


    stdio.start_loading("ob-configserver program health check")
    time.sleep(1)
    failed = []
    servers = cluster_config.servers
    count = 600
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            if server in tmp_servers:
                continue
            client = clients[server]
            server_config = cluster_config.get_server_conf(server)
            home_path = server_config["home_path"]
            pid_path = '%s/run/ob-configserver.pid' % home_path
            stdio.verbose('%s program health check' % server)
            pid = client.execute_command("cat %s" % pid_path).stdout.strip()
            if pid:
                if client.execute_command('ls /proc/%s' % pid):
                    stdio.verbose('%s ob-configserver[pid: %s] started', server, pid)
                elif count:
                    tmp_servers.append(server)
                else:
                    failed.append(server)
            else:
                failed.append(server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)

    if failed:
        stdio.stop_loading('fail')
        for server in failed:
            stdio.error(EC_OBC_PROGRAM_START_ERROR.format(server=server))
        plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true()