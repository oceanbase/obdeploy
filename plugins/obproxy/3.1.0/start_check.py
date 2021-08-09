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


stdio = None
success = True


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp,udp}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def start_check(plugin_context, strict_check=False, *args, **kwargs):
    def alert(*arg, **kwargs):
        global success
        if strict_check:
            success = False
            stdio.error(*arg, **kwargs)
        else:
            stdio.warn(*arg, **kwargs)
    def critical(*arg, **kwargs):
        global success
        success = False
        stdio.error(*arg, **kwargs)
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_port = {}
    stdio.start_loading('Check before start obproxy')
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        port = int(server_config["listen_port"])
        prometheus_port = int(server_config["prometheus_listen_port"])
        remote_pid_path = "%s/run/obproxy-%s-%s.pid" % (server_config['home_path'], server.ip, server_config["listen_port"])
        remote_pid = client.execute_command("cat %s" % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue
        
        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]
        server_config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('%s port check' % server)
        for key in ['listen_port', 'prometheus_listen_port']:
            port = int(server_config[key])
            alert_f = alert if key == 'prometheus_listen_port' else critical
            if port in ports:
                alert_f('Configuration conflict %s: %s port is used for %s\'s %s' % (server, port, ports[port]['server'], ports[port]['key']))
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                alert_f('%s:%s port is already used' % (ip, port))
                
    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')