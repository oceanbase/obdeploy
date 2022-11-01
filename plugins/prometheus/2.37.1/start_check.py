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

from _errno import EC_CONFIG_CONFLICT_PORT

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

    def critical(*arg, **kwargs):
        global success
        success = False
        stdio.error(*arg, **kwargs)

    global stdio, success
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_clients = {}
    servers_port = {}
    depends = ['obagent']
    username = None
    password = None
    for comp in cluster_config.depends:
        if comp in depends:
            for server in cluster_config.get_depend_servers(comp):
                obagent_config = cluster_config.get_depend_config(comp, server)
                check_ret = True
                if username is not None and username != obagent_config.get('http_basic_auth_user', ''):
                    check_ret = False
                if password is not None and password != obagent_config.get('http_basic_auth_password', ''):
                    check_ret = False
                if not check_ret:
                    stdio.warn('The http basic auth of obagent is inconsistent, and some targets in the scrape_configs may not work.')
                    break
                password = obagent_config.get('http_basic_auth_password', '')
                username = obagent_config.get('http_basic_auth_user', '')

    stdio.start_loading('Check before start prometheus')
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        servers_clients[ip] = client
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/prometheus.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]
        stdio.verbose('%s port check' % server)
        for key in ['port']:
            port = int(server_config[key])
            if port in ports:
                critical(EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'],
                                                        key=ports[port]['key']))
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                critical('%s:%s port is already used' % (ip, port))
    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')