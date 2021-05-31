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

import re


stdio = None
success = True


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'([1-9][0-9]*)([B,K,M,G,T])', size)
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "cat  /proc/net/{tcp,udp} | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def start_check(plugin_context, alert_lv='error', *args, **kwargs):
    def alert(*arg, **kwargs):
        global success
        success = False
        alert_f(*arg, **kwargs)
    global stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    alert_f = getattr(stdio, alert_lv)
    servers_clients = {}
    servers_port = {}
    servers_memory = {}
    servers_disk = {}
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        servers_clients[ip] = client
        if ip not in servers_port:
            servers_disk[ip] = {}
            servers_port[ip] = {}
            servers_memory[ip] = {'num': 0, 'percentage': 0}
        memory = servers_memory[ip]
        ports = servers_port[ip]
        disk = servers_disk[ip]
        server_config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('%s port check' % server)
        for key in ['mysql_port', 'rpc_port']:
            port = int(server_config[key])
            if port in ports:
                alert('%s: %s port is used for %s\'s %s' % (server, port, ports[port]['server'], ports[port]['key']))
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                alert('%s:%s port is already used' % (ip, port))
        if 'memory_limit' in server_config:
            memory['num'] += parse_size(server_config['memory_limit'])
        elif 'memory_limit_percentage' in server_config:
            memory['percentage'] += int(parse_size(server_config['memory_limit_percentage']))
        else:
            memory['percentage'] += 80
        data_path = server_config['data_dir'] if 'data_dir' in server_config else server_config['home_path']
        if data_path not in disk:
            disk[data_path] = 0
        if 'datafile_disk_percentage' in server_config:
            disk[data_path] += int(server_config['datafile_disk_percentage'])
        else:
            disk[data_path] += 90

    for ip in servers_clients:
        client = servers_clients[ip]
        ret = client.execute_command('cat /proc/sys/fs/aio-max-nr')
        if not ret or not ret.stdout.strip().isdigit():
            alert('(%s) failed to get fs.aio-max-nr' % ip)
        elif int(ret.stdout) < 1048576:
            alert('(%s) fs.aio-max-nr must not be less than 1048576 (Current value: %s)' % (ip, ret.stdout.strip()))

        ret = client.execute_command('ulimit -n')
        if not ret or not ret.stdout.strip().isdigit():
            alert('(%s) failed to get open files number' % ip)
        elif int(ret.stdout) < 655350:
            alert('(%s) open files number must not be less than 655350 (Current value: %s)' % (ip, ret.stdout.strip()))

        # memory
        if servers_memory[ip]['percentage'] > 100:
            alert('(%s) not enough memory' % ip)
        else:
            ret = client.execute_command("free -b | grep Mem | awk -F' ' '{print $2, $4}'")
            if ret:
                total_memory, free_memory = ret.stdout.split(' ')
                total_memory = int(total_memory)
                free_memory = int(free_memory)
                total_use = servers_memory[ip]['percentage'] * total_memory / 100 + servers_memory[ip]['num']
                if total_use > free_memory:
                    alert('(%s) not enough memory' % ip)
        # disk
        disk = {'/': 0}
        ret = client.execute_command('df -h')
        if ret:
            for v, p in re.findall('(\d+)%\s+(.+)', ret.stdout):
                disk[p] = int(v)
        for path in servers_disk[ip]:
            kp = '/'
            for p in disk:
                if p in path:
                    if len(p) > len(kp):
                        kp = p
            disk[kp] += servers_disk[ip][path]
            if disk[kp] > 100:
                alert('(%s) %s not enough disk space' % (ip, kp))

    if success:
        plugin_context.return_true()