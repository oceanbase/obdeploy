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

import os
import re


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


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'([1-9][0-9]*)\s*([B,K,M,G,T])', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def formate_size(size):
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    idx = 0
    while idx < 5 and size >= 1024:
        size /= 1024.0
        idx += 1
    return '%.1f%s' % (size, units[idx])


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
    servers_clients = {}
    servers_port = {}
    servers_memory = {}
    servers_disk = {}
    server_num = len(cluster_config.servers)
    stdio.start_loading('Check before start observer')
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/observer.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        servers_clients[ip] = client
        if ip not in servers_port:
            servers_disk[ip] = {}
            servers_port[ip] = {}
            servers_memory[ip] = {'num': 0, 'percentage': 0}
        memory = servers_memory[ip]
        ports = servers_port[ip]
        disk = servers_disk[ip]
        stdio.verbose('%s port check' % server)
        for key in ['mysql_port', 'rpc_port']:
            port = int(server_config[key])
            if port in ports:
                critical('Configuration conflict %s: %s port is used for %s\'s %s' % (server, port, ports[port]['server'], ports[port]['key']))
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                critical('%s:%s port is already used' % (ip, port))
        if 'memory_limit' in server_config:
            memory['num'] += parse_size(server_config['memory_limit'])
        elif 'memory_limit_percentage' in server_config:
            memory['percentage'] += int(parse_size(server_config['memory_limit_percentage']))
        else:
            memory['percentage'] += 80
        data_path = server_config['data_dir'] if 'data_dir' in server_config else  os.path.join(server_config['home_path'], 'store')
        if not client.execute_command('ls %s/sstable/block_file' % data_path):
            if data_path in disk:
                critical('Same Path: %s in %s and %s' % (data_path, server, disk[data_path]['server']))
                continue
            disk[data_path] = {
                'need': 90,
                'server': server
            }
            if 'datafile_size' in server_config and server_config['datafile_size']:
                disk[data_path]['need'] = server_config['datafile_size']
            elif 'datafile_disk_percentage' in server_config and server_config['datafile_disk_percentage']:
                disk[data_path]['need'] = int(server_config['datafile_disk_percentage'])

    for ip in servers_clients:
        client = servers_clients[ip]
        ret = client.execute_command('cat /proc/sys/fs/aio-max-nr /proc/sys/fs/aio-nr')
        if not ret:
            alert('(%s) failed to get fs.aio-max-nr and fs.aio-nr' % ip)
        else:
            try:
                max_nr, nr = ret.stdout.strip().split('\n')
                max_nr, nr = int(max_nr), int(nr)
                need = server_num * 20000
                if need > max_nr - nr:
                    critical('(%s) Insufficient AIO remaining (Avail: %s, Need: %s), The recommended value of fs.aio-max-nr is 1048576' % (ip, max_nr - nr, need))
                elif int(max_nr) < 1048576:
                    alert('(%s) The recommended value of fs.aio-max-nr is 1048576 (Current value: %s)' % (ip, max_nr))
            except:
                alert('(%s) failed to get fs.aio-max-nr and fs.aio-nr' % ip)
                stdio.exception('')

        ret = client.execute_command('ulimit -n')
        if not ret or not ret.stdout.strip().isdigit():
            alert('(%s) failed to get open files number' % ip)
        else:
            max_of = int(ret.stdout)
            need = server_num * 20000
            if need > max_of:
                critical('(%s) open files number must not be less than %s (Current value: %s)' % (ip, need, max_of))
            elif max_of < 655350:
                alert('(%s) The recommended number of open files is 655350 (Current value: %s)' % (ip, max_of))

        # memory
        ret = client.execute_command('cat /proc/meminfo')
        if ret:
            total_memory = 0
            free_memory = 0
            for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                if k == 'MemTotal':
                    total_memory = parse_size(str(v))
                elif k == 'MemAvailable':
                    free_memory = parse_size(str(v))
            total_use = servers_memory[ip]['percentage'] * total_memory / 100 + servers_memory[ip]['num']
            if total_use > free_memory:
                critical('(%s) not enough memory. (Free: %s, Need: %s)' % (ip, formate_size(free_memory), formate_size(total_use)))
        # disk
        disk = {'/': 0}
        ret = client.execute_command('df --output=size,avail,target')
        if ret:
            for total, avail, path in re.findall('(\d+)\s+(\d+)\s+(.+)', ret.stdout):
                disk[path] = {
                    'toatl': int(total) << 10,
                    'avail': int(avail) << 10,
                    'need': 0
                }
        for path in servers_disk[ip]:
            kp = '/'
            for p in disk:
                if p in path:
                    if len(p) > len(kp):
                        kp = p
            need = servers_disk[ip][path]['need']
            if isinstance(need, int):
                disk[kp]['need'] += disk[kp]['toatl'] * need / 100
            else:
                disk[kp]['need'] += parse_size(need)
        
        for p in disk:
            avail = disk[p]['avail']
            need = disk[p]['need']
            if need > avail:
                critical('(%s) %s not enough disk space. (Avail: %s, Need: %s)' % (ip, kp, formate_size(avail), formate_size(need)))

    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')