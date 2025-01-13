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


def get_port_socket_inode(client, port, stdio):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    inode = res.stdout.strip()
    if not res or not inode:
        return False
    stdio.verbose("inode: %s" % inode)
    return inode.split('\n')


def confirm_port(client, pid, port, stdio):
    socket_inodes = get_port_socket_inode(client, port, stdio)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def stop(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    servers = {}
    stdio.start_loading('Stop prometheus')
    success = True
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        prometheus_pid_path = os.path.join(home_path, 'run/prometheus.pid')
        prometheusd_pid_path = os.path.join(home_path, 'run/prometheusd.pid')
        prometheus_pid = client.execute_command('cat {}'.format(prometheus_pid_path)).stdout.strip()
        if prometheus_pid and client.execute_command('ls /proc/{}'.format(prometheus_pid)):
            if client.execute_command('ls /proc/%s/fd' % prometheus_pid):
                stdio.verbose('{} prometheus[pid:{}] stopping...'.format(server, prometheus_pid))
                client.execute_command('cat {} | xargs kill -9; kill -9 {}'.format(prometheusd_pid_path, prometheus_pid))
                servers[server] = {
                    'client': client,
                    'port': server_config['port'],
                    'pid': prometheus_pid,
                    'path': prometheus_pid_path
                }
            else:
                stdio.verbose('failed to stop prometheus[pid:{}] in {}, permission deny'.format(prometheus_pid, server))
                success = False
        else:
            stdio.verbose('{} prometheus is not running'.format(server))
    if not success:
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    count = 10
    check = lambda client, pid, port: confirm_port(client, pid, port, stdio) if count < 5 else get_port_socket_inode(client, port, stdio)
    time.sleep(1)
    while count and servers:
        tmp_servers = {}
        for server in servers:
            data = servers[server]
            client = clients[server]
            stdio.verbose('%s check whether the port is released' % server)
            for key in ['port']:
                if data[key] and check(data['client'], data['pid'], data[key]):
                    tmp_servers[server] = data
                    break
                data[key] = ''
            else:
                client.execute_command('rm -f %s' % data['path'])
                stdio.verbose('%s prometheus is stopped', server)
        servers = tmp_servers
        count -= 1
        if count and servers:
            time.sleep(3)

    if servers:
        stdio.stop_loading('fail')
        for server in servers:
            stdio.warn('%s port not released', server)
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
