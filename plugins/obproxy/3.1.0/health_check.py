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
import re
import time

from tool import confirm_port


def confirm_home_path(client, pid, home_path):
    if client.execute_command('path=`ls -l /proc/%s | grep cwd | awk -F\'-> \' \'{print $2}\'`; bash -c \'if [ "$path" != "%s" ]; then exit 1; fi\'' % (pid, home_path)):
        return True
    return False


def confirm_command(client, pid, command):
    command = command.replace(' ', '').strip()
    if client.execute_command('bash -c \'cmd=`cat /proc/%s/cmdline`; if [ "$cmd" != "%s" ]; then exit 1; fi\'' % (pid, command)):
        return True
    return False


def is_started(client, remote_bin_path, port, home_path, command):
    username = client.config.username
    ret = client.execute_command('pgrep -u %s -f "^%s"' % (username, remote_bin_path))
    if not ret:
        return False
    pids = ret.stdout.strip()
    if not pids:
        return False
    pids = pids.split('\n')
    for pid in pids:
        if confirm_port(client, pid, port):
            break
    else:
        return False
    return confirm_home_path(client, pid, home_path) and confirm_command(client, pid, command)


def obproxyd(home_path, client, ip, port):
    path = os.path.join(os.path.split(__file__)[0], 'obproxyd.sh')
    retmoe_path = os.path.join(home_path, 'obproxyd.sh')
    if os.path.exists(path):
        shell = '''bash %s %s %s %s''' % (retmoe_path, home_path, ip, port)
        return client.put_file(path, retmoe_path) and client.execute_command(shell)
    return False


def health_check(plugin_context, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    pid_path = plugin_context.get_variable('pid_path')

    stdio.start_loading('obproxy program health check')
    failed = []
    servers = cluster_config.servers
    count = 600
    while servers and count:
        count -= 1
        tmp_servers = []
        for server in servers:
            server_config = cluster_config.get_server_conf(server)
            client = clients[server]
            stdio.verbose('%s program health check' % server)
            remote_pid = client.execute_command("cat %s" % pid_path[server]).stdout.strip()
            if remote_pid:
                for pid in re.findall('\d+',remote_pid):
                    confirm = confirm_port(client, pid, int(server_config["listen_port"]))
                    if confirm:
                        proxyd_Pid_path = os.path.join(server_config["home_path"], 'run/obproxyd-%s-%d.pid' % (server.ip, server_config["listen_port"]))
                        if client.execute_command("pid=`cat %s` && ls /proc/$pid" % proxyd_Pid_path):
                            stdio.verbose('%s obproxy[pid: %s] started', server, pid)
                        else:
                            client.execute_command('echo %s > %s' % (pid, pid_path[server]))
                            obproxyd(server_config["home_path"], client, server.ip, server_config["listen_port"])
                            tmp_servers.append(server)
                        break
                    stdio.verbose('failed to start %s obproxy, remaining retries: %d' % (server, count))
                    if count:
                        tmp_servers.append(server)
                    else:
                        failed.append('failed to start %s obproxy' % server)
            else:
                failed.append('failed to start %s obproxy' % server)
        servers = tmp_servers
        if servers and count:
            time.sleep(1)
    if failed:
        stdio.stop_loading('fail')
        for msg in failed:
            stdio.warn(msg)
        plugin_context.return_false()
    else:
        stdio.stop_loading('succeed')
        plugin_context.return_true(need_bootstrap=need_bootstrap)