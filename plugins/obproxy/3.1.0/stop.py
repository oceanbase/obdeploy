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


from __future__ import absolute_import, division, print_function

import time


stdio = None


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "cat  /proc/net/{tcp,udp} | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    inode = res.stdout.strip()
    if not res or not inode:
        return False
    stdio.verbose("inode: %s" % inode)
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
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    servers = {}
    stdio.start_loading('Stop obproxy')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        if 'home_path' not in server_config:
            stdio.verbose('%s home_path is empty', server)
            continue
        remote_pid_path = '%s/run/obproxy-%s-%s.pid' % (server_config["home_path"], server.ip, server_config["listen_port"])
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                stdio.verbose('%s obproxy[pid:%s] stopping ...' % (server, remote_pid))
                client.execute_command('kill -9 -%s' % remote_pid)
                servers[server] = {
                    'client': client,
                    'listen_port': server_config['listen_port'],
                    'prometheus_listen_port': server_config['prometheus_listen_port'],
                    'pid': remote_pid,
                    'path': remote_pid_path
                }
        else:
            stdio.verbose('%s obproxy is not running' % server)

    count = 10
    check = lambda client, pid, port: confirm_port(client, pid, port) if count < 5 else get_port_socket_inode(client, port)
    time.sleep(1)
    while count and servers:
        tmp_servers = {}
        for server in servers:
            data = servers[server]
            stdio.verbose('%s check whether the port is released' % server)
            for key in ['prometheus_listen_port', 'listen_port']:
                if data[key] and check(data['client'], data['pid'], data[key]):
                    tmp_servers[server] = data
                    break
                data[key] = ''
            else:
                client.execute_command('rm -f %s' % data['path'])
                stdio.verbose('%s obproxy is stopped', server)
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
        plugin_context.return_true()