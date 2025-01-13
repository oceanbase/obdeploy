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

import re
import os
import time

import _errno as err
from _types import Capacity
from tool import get_disk_info


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
                    memory_limit = server_memory_config[server]['percentage'] * server_memory_stats['total'] / 100

                factor = 0.7
                suggest = err.SUG_OBSERVER_SYS_MEM_TOO_LARGE.format(factor=factor)
                suggest.auto_fix = 'system_memory' not in global_generate_config and 'system_memory' not in generate_configs.get(server, {})
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

    global_generate_config = generate_configs.get('global', {})
    START_NEED_MEMORY = 3 << 30

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
            kp = '/'
            for p in disk:
                if p in path:
                    if len(p) > len(kp):
                        kp = p
            need = servers_disk[ip][path]['need']
            if isinstance(need, int):
                disk[kp]['need'] += disk[kp]['total'] * need / 100
            else:
                disk[kp]['need'] += Capacity(need).bytes

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
            suggests = []
            if need > 0 and threshold < 2:
                suggests.append(err.SUG_OBSERVER_SAME_DISK.format())
                for server in ip_servers:
                    alert(server, 'disk', err.WC_OBSERVER_SAME_DISK.format(ip=ip, disk=p), suggests)
            if need > avail:
                for server in ip_servers:
                    server_generate_config = generate_configs.get(server, {})
                    suggest = err.SUG_OBSERVER_NOT_ENOUGH_DISK.format()
                    suggest.auto_fix = True
                    for key in ['datafile_size', 'datafile_disk_percentage']:
                        if key in global_generate_config or key in server_generate_config:
                            suggest.auto_fix = False
                            break
                    critical(server, 'disk', err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=p, avail=str(Capacity(avail)), need=str(Capacity(need))), [suggest] + suggests)
            elif 1.0 * (total - avail + need) / total > disk[p]['threshold']:
                # msg = '(%s) %s not enough disk space for clog. Use `redo_dir` to set other disk for clog' % (ip, p)
                # msg += ', or reduce the value of `datafile_size`' if need > 0 else '.'
                # critical(msg)
                for server in ip_servers:
                    server_generate_config = generate_configs.get(server, {})
                    suggest = err.SUG_OBSERVER_NOT_ENOUGH_DISK_4_CLOG.format()
                    suggest.auto_fix = True
                    for key in ['clog_disk_utilization_threshold', 'clog_disk_usage_limit_percentage']:
                        if key in global_generate_config or key in server_generate_config:
                            suggest.auto_fix = False
                            break
                critical(server, 'disk', err.EC_OBSERVER_NOT_ENOUGH_DISK_4_CLOG.format(ip=ip, path=p), [suggest] + suggests)
    success = plugin_context.get_variable('get_success')()
    if success:
        times = []
        for ip in servers_clients:
            client = servers_clients[ip]
            delta = time_delta(client)
            stdio.verbose('%s time delta %s' % (ip, delta))
            times.append(delta)
        if times and max(times) - min(times) > 200:
            critical(server, 'ntp', err.EC_OBSERVER_TIME_OUT_OF_SYNC, [err.SUG_OBSERVER_TIME_OUT_OF_SYNC.format()])

    for server in cluster_config.servers:
        wait_2_pass(server)
    success = plugin_context.get_variable('get_success')()
    plugin_context.set_variable("ip_servers", ip_servers)
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()

