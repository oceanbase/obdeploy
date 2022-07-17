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
import time

from _errno import EC_OBSERVER_NOT_ENOUGH_DISK_4_CLOG, EC_CONFIG_CONFLICT_PORT, EC_OBSERVER_NOT_ENOUGH_MEMORY, EC_ULIMIT_CHECK, WC_ULIMIT_CHECK


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


def format_size(size):
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    idx = 0
    while idx < 5 and size >= 1024:
        size /= 1024.0
        idx += 1
    return '%.1f%s' % (size, units[idx])


def time_delta(client):
    time_st = time.time() * 1000
    time_srv = int(client.execute_command('date +%s%N').stdout) / 1000000
    time_ed = time.time() * 1000

    time_it = time_ed - time_st
    time_srv -= time_it
    return time_srv - time_st


def _start_check(plugin_context, strict_check=False, *args, **kwargs):
    def alert(*arg, **kwargs):
        global success
        if strict_check:
            success = False
            stdio.error(*arg, **kwargs)
        else:
            stdio.warn(*arg, **kwargs)
    def error(*arg, **kwargs):
        global success
        if plugin_context.dev_mode:
            stdio.warn(*arg, **kwargs)
        else:
            success = False
            stdio.error(*arg, **kwargs)
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
    servers_clog_mount = {}
    servers_net_inferface = {}
    server_num = len(cluster_config.servers)
    stdio.start_loading('Check before start observer')
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        servers_clients[ip] = client
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        remote_pid_path = '%s/run/observer.pid' % home_path
        remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
        if remote_pid:
            if client.execute_command('ls /proc/%s' % remote_pid):
                continue

        if ip not in servers_port:
            servers_disk[ip] = {}
            servers_port[ip] = {}
            servers_clog_mount[ip] = {}
            servers_net_inferface[ip] = {}
            servers_memory[ip] = {'num': 0, 'percentage': 0}
        memory = servers_memory[ip]
        ports = servers_port[ip]
        disk = servers_disk[ip]
        clog_mount = servers_clog_mount[ip]
        inferfaces = servers_net_inferface[ip]
        stdio.verbose('%s port check' % server)
        for key in ['mysql_port', 'rpc_port']:
            port = int(server_config[key])
            if port in ports:
                critical(EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']))
                continue
            ports[port] = {
                'server': server,
                'key': key
            }
            if get_port_socket_inode(client, port):
                critical('%s:%s port is already used' % (ip, port))
        if 'memory_limit' in server_config:
            try:
                memory['num'] += parse_size(server_config['memory_limit'])
            except:
                error('memory_limit must be an integer')
                return
        elif 'memory_limit_percentage' in server_config:
            try:
                memory['percentage'] += int(parse_size(server_config['memory_limit_percentage']))
            except:
                error('memory_limit_percentage must be an integer')
                return
        else:
            memory['percentage'] += 80
        data_path = server_config['data_dir'] if server_config.get('data_dir') else  os.path.join(server_config['home_path'], 'store')
        redo_dir = server_config['redo_dir'] if server_config.get('redo_dir') else  data_path
        clog_dir = server_config['clog_dir'] if server_config.get('clog_dir') else  os.path.join(redo_dir, 'clog')
        if not client.execute_command('ls %s/sstable/block_file' % data_path):
            if data_path in disk:
                critical('Same Path: %s in %s and %s' % (data_path, server, disk[data_path]['server']))
                continue
            if clog_dir in clog_mount:
                critical('Same Path: %s in %s and %s' % (clog_dir, server, clog_mount[clog_dir]['server']))
                continue
            disk[data_path] = {
                'need': 90,
                'server': server
            }
            clog_mount[clog_dir] = {
                'threshold': server_config.get('clog_disk_utilization_threshold', 80) / 100.0,
                'server': server
            }
            if 'datafile_size' in server_config and server_config['datafile_size']:
                disk[data_path]['need'] = server_config['datafile_size']
            elif 'datafile_disk_percentage' in server_config and server_config['datafile_disk_percentage']:
                disk[data_path]['need'] = int(server_config['datafile_disk_percentage'])
            
            devname = server_config.get('devname')
            if devname:
                if not client.execute_command("grep -e '^ *%s:' /proc/net/dev" % devname):
                    critical('%s No such net interface: %s' % (server, devname))
            if devname not in inferfaces:
                inferfaces[devname] = []
            inferfaces[devname].append(ip)

    for ip in servers_disk:
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

        ret = client.execute_command('ulimit -a')
        ulimits_min = {
            'open files': {
                'need': lambda x: 20000 * x,
                'recd': lambda x: 655350
            },
            'max user processes': {
                'need': lambda x: 4096,
                'recd': lambda x: 4096 * x
            },
        }
        ulimits = {}
        src_data = re.findall('\s?([a-zA-Z\s]+[a-zA-Z])\s+\([a-zA-Z\-,\s]+\)\s+([\d[a-zA-Z]+)', ret.stdout) if ret else []
        for key, value in src_data:
            ulimits[key] = value
        for key in ulimits_min:
            value = ulimits.get(key)
            if value == 'unlimited':
                continue
            if not value or not (value.strip().isdigit()):
                alert('(%s) failed to get %s' % (ip, key))
            else:
                value = int(value)
                need = ulimits_min[key]['need'](server_num)
                if need > value:
                    critical(EC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value))
                else:
                    need = ulimits_min[key]['recd'](server_num)
                    if need > value:
                        alert(WC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value))

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
                error(EC_OBSERVER_NOT_ENOUGH_MEMORY.format(ip=ip, free=format_size(free_memory), need=format_size(total_use)))
        # disk
        disk = {'/': 0}
        ret = client.execute_command('df --block-size=1024')
        if ret:
            for total, used, avail, puse, path in re.findall('(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
                disk[path] = {
                    'total': int(total) << 10,
                    'avail': int(avail) << 10,
                    'need': 0,
                    'threshold': 2
                }
        all_path = set(list(servers_disk[ip].keys()) + list(servers_clog_mount[ip].keys()))
        for include_dir in all_path:
            while include_dir not in disk:
                ret = client.execute_command('df --block-size=1024 %s' % include_dir)
                if ret:
                    for total, used, avail, puse, path in re.findall('(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)',
                                                                     ret.stdout):
                        disk[path] = {
                            'total': int(total) << 10,
                            'avail': int(avail) << 10,
                            'need': 0,
                            'threshold': 2
                        }
                    break
                else:
                    include_dir = os.path.dirname(include_dir)
        stdio.verbose('disk: {}'.format(disk))
        for path in servers_disk[ip]:
            kp = '/'
            for p in disk:
                if p in path:
                    if len(p) > len(kp):
                        kp = p
            need = servers_disk[ip][path]['need']
            if isinstance(need, int):
                disk[kp]['need'] += disk[kp]['total'] * need / 100
            else:
                try:
                    disk[kp]['need'] += parse_size(need)
                except:
                    critical('datafile_size must be an integer')
                    return
        
        for path in servers_clog_mount[ip]:
            kp = '/'
            for p in disk:
                if p in path:
                    if len(p) > len(kp):
                        kp = p
            disk[kp]['threshold'] = min(disk[kp]['threshold'], servers_clog_mount[ip][path]['threshold'])
            
        for p in disk:
            total = disk[p]['total']
            avail = disk[p]['avail']
            need = disk[p]['need']
            threshold = disk[p]['threshold']
            if need > 0 and threshold < 2:
                alert('(%s) clog and data use the same disk (%s)' % (ip, p))
            if need > avail:
                critical('(%s) %s not enough disk space. (Avail: %s, Need: %s)' % (ip, p, format_size(avail), format_size(need)))
            elif 1.0 * (total - avail + need) / total > disk[p]['threshold']:
                # msg = '(%s) %s not enough disk space for clog. Use `redo_dir` to set other disk for clog' % (ip, p)
                # msg += ', or reduce the value of `datafile_size`' if need > 0 else '.'
                # critical(msg)
                critical(EC_OBSERVER_NOT_ENOUGH_DISK_4_CLOG.format(ip=ip, path=p))

    if success:
        for ip in servers_net_inferface:
            if servers_net_inferface[ip].get(None):
                devinfo = client.execute_command('cat /proc/net/dev').stdout
                interfaces = []
                for interface in re.findall('\n\s+(\w+):', devinfo):
                    if interface != 'lo':
                        interfaces.append(interface)
                if not interfaces:
                    interfaces = ['lo']
                if len(interfaces) > 1:
                    servers = ','.join(str(server) for server in servers_net_inferface[ip][None])
                    critical('%s has more than one network inferface. Please set `devname` for (%s)' % (ip, servers))
                else:
                    servers_net_inferface[ip][interfaces[0]] = servers_net_inferface[ip][None]
                    del servers_net_inferface[ip][None]
    if success:
        for ip in servers_net_inferface:
            client = servers_clients[ip]
            for devname in servers_net_inferface[ip]:
                if client.is_localhost() and devname != 'lo' or (not client.is_localhost() and devname == 'lo'):
                        critical('%s %s fail to ping %s. Please check configuration `devname`' % (server, devname, ip))
                        continue
                for _ip in servers_clients:
                    if ip == _ip:
                        continue
                    if not client.execute_command('ping -W 1 -c 1 -I %s %s' % (devname, _ip)):
                        critical('%s %s fail to ping %s. Please check configuration `devname`' % (server, devname, _ip))
                        break

    if success:
        times = []
        for ip in servers_clients:
            client = servers_clients[ip]
            delta = time_delta(client)
            stdio.verbose('%s time delta %s' % (ip, delta))
            times.append(delta)
        if times and max(times) - min(times) > 200:
            critical('Cluster NTP is out of sync')


def start_check(plugin_context, strict_check=False, *args, **kwargs):
    _start_check(plugin_context, strict_check)
    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
