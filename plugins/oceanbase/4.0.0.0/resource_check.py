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
import os
import time

import _errno as err
from _types import Capacity


def get_disk_info_by_path(path, client, stdio):
    disk_info = {}
    ret = client.execute_command('df --block-size=1024 {}'.format(path))
    if ret:
        for total, used, avail, puse, path in re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
            disk_info[path] = {'total': int(total) << 10, 'avail': int(avail) << 10, 'need': 0}
            stdio.verbose('get disk info for path {}, total: {} avail: {}'.format(path, disk_info[path]['total'], disk_info[path]['avail']))
    return disk_info


def get_disk_info(all_paths, client, stdio):
    overview_ret = True
    disk_info = get_disk_info_by_path('', client, stdio)
    if not disk_info:
        overview_ret = False
        disk_info = get_disk_info_by_path('/', client, stdio)
        if not disk_info:
            disk_info['/'] = {'total': 0, 'avail': 0, 'need': 0}
    all_path_success = {}
    for path in all_paths:
        all_path_success[path] = False
        cur_path = path
        while cur_path not in disk_info:
            disk_info_for_current_path = get_disk_info_by_path(cur_path, client, stdio)
            if disk_info_for_current_path:
                disk_info.update(disk_info_for_current_path)
                all_path_success[path] = True
                break
            else:
                cur_path = os.path.dirname(cur_path)
    if overview_ret or all(all_path_success.values()):
        return disk_info


def get_mount_path(disk, _path):
    _mount_path = '/'
    for p in disk:
        if p in _path and _path.startswith(p):
            if len(p) > len(_mount_path):
                _mount_path = p
    return _mount_path


def time_delta(client):
    time_st = time.time() * 1000
    time_srv = int(client.execute_command('date +%s%N').stdout) / 1000000
    time_ed = time.time() * 1000

    time_it = time_ed - time_st
    time_srv -= time_it/2
    return time_srv - time_st


def resource_check(plugin_context, generate_configs={}, strict_check=False, *args, **kwargs):
    def system_memory_check():
        server_memory_config = server_memory_stat['servers']
        for server in server_memory_config:
            if server_memory_config[server]['system_memory']:
                memory_limit = server_memory_config[server]['num']
                if not memory_limit:
                    server_memory_config[server]['num'] = memory_limit = server_memory_config[server]['percentage'] * server_memory_stats['total'] / 100
                factor = 0.75
                suggest = err.SUG_OBSERVER_SYS_MEM_TOO_LARGE.format(factor=factor)
                suggest.auto_fix = 'system_memory' not in global_generate_config and 'system_memory' not in generate_configs.get(server, {})
                global success
                if memory_limit <= server_memory_config[server]['system_memory']:
                    critical(server, 'mem', err.EC_OBSERVER_SYS_MEM_TOO_LARGE.format(server=server), [suggest])
                elif memory_limit * factor < server_memory_config[server]['system_memory']:
                    alert(server, 'mem', err.WC_OBSERVER_SYS_MEM_TOO_LARGE.format(server=server, factor=factor), [suggest])

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    servers_clients = plugin_context.get_variable('servers_clients')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    alert = plugin_context.get_variable('alert')
    error = plugin_context.get_variable('error')
    critical = plugin_context.get_variable('critical')
    servers_memory = plugin_context.get_variable('servers_memory')
    servers_clog_mount = plugin_context.get_variable('servers_clog_mount')
    success = plugin_context.get_variable('success')

    global_generate_config = generate_configs.get('global', {})
    START_NEED_MEMORY = 3 << 30
    servers_log_disk_size = {}
    ip_server_memory_info = {}

    servers_disk = plugin_context.get_variable('need_check_servers_disk')
    ip_servers = []
    for ip in servers_disk:
        client = servers_clients[ip]
        ip_servers = servers_memory[ip]['servers'].keys()
        server_num = len(ip_servers)

        # memory
        ret = client.execute_command('cat /proc/meminfo')
        if ret:
            server_memory_stats = {}
            memory_key_map = {
                'MemTotal': 'total',
                'MemFree': 'free',
                'MemAvailable': 'available',
                'Buffers': 'buffers',
                'Cached': 'cached'
            }
            for key in memory_key_map:
                server_memory_stats[memory_key_map[key]] = 0
            for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                if k in memory_key_map:
                    key = memory_key_map[k]
                    server_memory_stats[key] = Capacity(str(v)).bytes

            ip_server_memory_info[ip] = server_memory_stats
            server_memory_stat = servers_memory[ip]
            min_start_need = server_num * START_NEED_MEMORY
            total_use = int(server_memory_stat['percentage'] * server_memory_stats['total'] / 100 + server_memory_stat['num'])
            if min_start_need > server_memory_stats['available']:
                for server in ip_servers:
                    error(server, 'mem', err.EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE.format(ip=ip, available=str(Capacity(server_memory_stats['available'])), need=str(Capacity(min_start_need))), [err.SUG_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE.format(ip=ip)])
            elif total_use > server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached']:
                for server in ip_servers:
                    server_generate_config = generate_configs.get(server, {})
                    suggest = err.SUG_OBSERVER_REDUCE_MEM.format()
                    suggest.auto_fix = True
                    for key in ['memory_limit', 'memory_limit_percentage']:
                        if key in global_generate_config or key in server_generate_config:
                            suggest.auto_fix = False
                            break
                    error(server, 'mem', err.EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=str(Capacity(server_memory_stats['free'])), cached=str(Capacity(server_memory_stats['buffers'] + server_memory_stats['cached'])), need=str(Capacity(total_use))), [suggest])
            elif total_use > server_memory_stats['free']:
                system_memory_check()
                for server in ip_servers:
                    alert(server, 'mem', err.EC_OBSERVER_NOT_ENOUGH_MEMORY.format(ip=ip, free=str(Capacity(server_memory_stats['free'])), need=str(Capacity(total_use))), [err.SUG_OBSERVER_REDUCE_MEM.format()])
            else:
                system_memory_check()

        # disk
        all_path = set(list(servers_disk[ip].keys()) + list(servers_clog_mount[ip].keys()))
        disk = get_disk_info(all_paths=all_path, client=client, stdio=stdio)
        stdio.verbose('disk: {}'.format(disk))
        for path in servers_disk[ip]:
            mount_path = get_mount_path(disk, path)
            need = servers_disk[ip][path].get('need')
            if not need:
                for clog_path in servers_clog_mount[ip]:
                    clog_mount_path = get_mount_path(disk, clog_path)
                    if clog_mount_path == mount_path:
                        need = 60
                        stdio.verbose('clog and data use the same disk, datadisk percentage: {}'.format(need))
                        break
                else:
                    need = 90
                    stdio.verbose('datadisk percentage: {}'.format(need))
            slog_size = plugin_context.get_variable('slog_size')
            if isinstance(need, int):
                # slog need 10G
                disk[mount_path]['need'] += max(disk[mount_path]['total'] - slog_size, 0) * need / 100
            else:
                disk[mount_path]['need'] += Capacity(need).bytes

            disk[mount_path]['need'] += slog_size
            disk[mount_path]['is_data_disk'] = True
        for path in servers_clog_mount[ip]:
            mount_path = get_mount_path(disk, path)
            if 'need' in servers_clog_mount[ip][path]:
                need = servers_clog_mount[ip][path]['need']
            elif disk[mount_path].get('is_data_disk'):
                # hard code
                need = 30
                stdio.verbose('clog and data use the same disk, clog percentage: {}'.format(need))
            else:
                need = 90
                stdio.verbose('clog percentage: {}'.format(need))
            if isinstance(need, int):
                # log_disk_percentage
                log_disk_size = disk[mount_path]['total'] * need / 100
            else:
                # log_disk_size
                log_disk_size = Capacity(need).bytes
            servers_log_disk_size[servers_clog_mount[ip][path]['server']] = log_disk_size
            disk[mount_path]['need'] += log_disk_size
            disk[mount_path]['is_clog_disk'] = True
        for p in disk:
            avail = disk[p]['avail']
            need = disk[p]['need']
            suggests = []
            if disk[p].get('is_data_disk') and disk[p].get('is_clog_disk'):
                suggests.append(err.SUG_OBSERVER_SAME_DISK.format())
                for server in ip_servers:
                    alert(server, 'disk', err.WC_OBSERVER_SAME_DISK.format(ip=ip, disk=p), suggests)
            if need > avail:
                suggest_temps = {
                    'data': {
                        'tmplate': err.SUG_OBSERVER_NOT_ENOUGH_DISK,
                        'keys': ['datafile_size', 'datafile_disk_percentage']
                    }
                }
                if suggests:
                    suggest_temps['mem'] = {
                        'tmplate': err.SUG_OBSERVER_REDUCE_MEM,
                        'keys': ['memory_limit', 'memory_limit_percentage']
                    }
                    suggest_temps['redo'] =  {
                        'tmplate': err.SUG_OBSERVER_REDUCE_REDO,
                        'keys': ['log_disk_size', 'log_disk_percentage']
                    }
                for server in ip_servers:
                    tmp_suggests = []
                    server_generate_config = generate_configs.get(server, {})
                    for item in suggest_temps:
                        suggest = suggest_temps[item]['tmplate'].format()
                        suggest.auto_fix = True
                        for key in suggest_temps[item]['keys']:
                            if key in global_generate_config or key in server_generate_config:
                                suggest.auto_fix = False
                                break
                        tmp_suggests.append(suggest)
                    tmp_suggests = sorted(tmp_suggests, key=lambda suggest: suggest.auto_fix, reverse=True)
                    critical(server, 'disk', err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=p, avail=str(Capacity(avail)), need=str(Capacity(need))), tmp_suggests + suggests)

    if success:
        times = []
        for ip in servers_clients:
            client = servers_clients[ip]
            delta = time_delta(client)
            stdio.verbose('%s time delta %s' % (ip, delta))
            times.append(delta)
        if times and max(times) - min(times) > 500:
            critical(server, 'ntp', err.EC_OBSERVER_TIME_OUT_OF_SYNC.format(), [err.SUG_OBSERVER_TIME_OUT_OF_SYNC.format()])
    plugin_context.set_variable("ip_servers", ip_servers)
    plugin_context.set_variable('servers_log_disk_size', servers_log_disk_size)
    return plugin_context.return_true()

