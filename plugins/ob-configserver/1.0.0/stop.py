# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.

import time


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/tcp*' | awk -F' ' '{print $2,$10}' | grep ':%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    inode = res.stdout.strip()
    if not res or not inode:
        return False
    return inode.split('\n')


def confirm_port(client, pid, port):
    socket_inodes = get_port_socket_inode(client, port)
    if not socket_inodes:
        return False
    ret = client.execute_command("ls -l /proc/%s/fd/ |grep -E 'socket:\[(%s)\]'" % (pid, '|'.join(socket_inodes)))
    if ret and ret.stdout.strip():
        return True
    return False


def stop(plugin_context, *args, **kwargs):
    global_ret = True
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('Stop ob-configserver')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config["home_path"]
        pid_path = '%s/run/ob-configserver.pid' % home_path
        pid = client.execute_command('cat %s' % pid_path).stdout.strip()
        if pid and client.execute_command('ls /proc/%s' % pid):
            if client.execute_command('ls /proc/%s/fd' % pid):
                stdio.verbose('%s ob-configserver[pid:%s] stopping ...' % (server, pid))
                client.execute_command('kill -9 %s' % pid)
            else:
                stdio.verbose('failed to stop ob-configserver[pid:%s] in %s, permission deny' % (pid, server))
                global_ret = False
                continue
        else:
            stdio.verbose('%s ob-configserver is not running' % server)
            continue

    if global_ret:
        servers = cluster_config.servers
        count = 10
        time.sleep(1)
        while count and servers:
            count -= 1
            tmp_servers = []
            for server in servers:
                server_config = cluster_config.get_server_conf(server)
                client = clients[server]
                home_path = server_config["home_path"]
                pid_path = '%s/run/ob-configserver.pid' % home_path
                pid = client.execute_command('cat %s' % pid_path).stdout.strip()
                port = int(server_config['listen_port'])
                stdio.verbose('%s check whether the port is released' % server)
                if not confirm_port(client, pid, port):
                    break
                elif count:
                    tmp_servers.append(server)
                else:
                    global_ret = False
                    stdio.warn('%s port not released', server)
            servers = tmp_servers
            if count and servers:
                time.sleep(3)

    if not global_ret:
        stdio.stop_loading('fail')
    else:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
