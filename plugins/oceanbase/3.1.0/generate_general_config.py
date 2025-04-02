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

from _types import Capacity
from _errno import EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE, EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED


def get_system_memory(memory_limit):
    if memory_limit <= (64 << 30):
        system_memory = memory_limit * 0.5
    elif memory_limit <= (150 << 30):
        system_memory = memory_limit * 0.4
    else:
        system_memory = memory_limit * 0.3
    system_memory = max(4 << 30, system_memory)
    return str(Capacity(system_memory, 0))


def generate_general_config(plugin_context, generate_config_mini=False, generate_check=True, generate_consistent_config=False, generate_password=True, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    generate_configs = plugin_context.get_variable('generate_configs')
    update_global_conf = plugin_context.get_variable('update_global_conf')
    update_server_conf = plugin_context.get_variable('update_server_conf')
    summit_config = plugin_context.get_variable('summit_config')
    generate_random_password = plugin_context.get_variable('generate_random_password')

    stdio.start_loading('Generate observer configuration')
    success = True
    MIN_MEMORY = 8 << 30
    MIN_CPU_COUNT = 8
    START_NEED_MEMORY = 3 << 30
    clog_disk_utilization_threshold_max = 95
    clog_disk_usage_limit_percentage_max = 98
    global_config = cluster_config.get_original_global_conf()

    max_syslog_file_count_default = 16
    if global_config.get('syslog_level') is None:
        update_global_conf('syslog_level', 'INFO')
    if global_config.get('enable_syslog_wf') is None:
        update_global_conf('enable_syslog_wf', False)
    if global_config.get('max_syslog_file_count') is None:
        update_global_conf('max_syslog_file_count', max_syslog_file_count_default)
    if global_config.get('cluster_id') is None:
        update_global_conf('cluster_id', 1)

    if generate_config_mini:
        if not global_config.get('memory_limit_percentage') and not global_config.get('memory_limit'):
            update_global_conf('memory_limit', str(Capacity(MIN_MEMORY, 0)))
        if not global_config.get('datafile_size') and not global_config.get('datafile_disk_percentage'):
            update_global_conf('datafile_size', '20G')
        if not global_config.get('clog_disk_utilization_threshold'):
            update_global_conf('clog_disk_utilization_threshold', clog_disk_utilization_threshold_max)
        if not global_config.get('clog_disk_usage_limit_percentage'):
            update_global_conf('clog_disk_usage_limit_percentage', clog_disk_usage_limit_percentage_max)
        summit_config()

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        user_server_config = cluster_config.get_original_server_conf_with_global(server, format_conf=True)

        if user_server_config.get('devname') is None:
            if client.is_localhost():
                update_server_conf(server, 'devname', 'lo')
            else:
                devinfo = client.execute_command('cat /proc/net/dev').stdout
                interfaces = re.findall('\n\s+(\w+):', devinfo)
                for interface in interfaces:
                    if interface == 'lo':
                        continue
                    if client.execute_command('ping -W 1 -c 1 -I %s %s' % (interface, ip)):
                        update_server_conf(server, 'devname', interface)
                        break

        dirs = {"home_path": server_config['home_path']}
        dirs["data_dir"] = server_config['data_dir'] if server_config.get('data_dir') else os.path.join(server_config['home_path'], 'store')
        dirs["redo_dir"] = server_config['redo_dir'] if server_config.get('redo_dir') else dirs["data_dir"]
        dirs["clog_dir"] = server_config['clog_dir'] if server_config.get('clog_dir') else os.path.join(dirs["redo_dir"], 'clog')

        # memory
        auto_set_memory = False
        if user_server_config.get('memory_limit_percentage'):
            ret = client.execute_command('cat /proc/meminfo')
            if ret:
                total_memory = 0
                for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                    if k == 'MemTotal':
                        total_memory = Capacity(str(v)).bytes
            memory_limit = int(total_memory * user_server_config.get('memory_limit_percentage') / 100)
        else:
            if not server_config.get('memory_limit'):
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

                    if generate_check:
                        if server_memory_stats['available'] < START_NEED_MEMORY:
                            stdio.error(EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE.format(ip=ip, available=Capacity(server_memory_stats['available']), need=Capacity(START_NEED_MEMORY)))
                            success = False
                            continue

                        if server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached'] < MIN_MEMORY:
                            stdio.error(EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=Capacity(server_memory_stats['free']), cached=Capacity(server_memory_stats['buffers'] + server_memory_stats['cached']), need=Capacity(MIN_MEMORY)))
                            success = False
                            continue

                    memory_limit = max(MIN_MEMORY, int(server_memory_stats['available'] * 0.9))
                    server_config['memory_limit'] = str(Capacity(memory_limit, 0))
                    update_server_conf(server, 'memory_limit', server_config['memory_limit'])
                    auto_set_memory = True
                else:
                    stdio.error("%s: fail to get memory info.\nPlease configure 'memory_limit' manually in configuration file")
                    success = False
                    continue
            else:
                memory_limit = Capacity(server_config.get('memory_limit')).bytes

        auto_set_system_memory = False
        if not user_server_config.get('system_memory'):
            auto_set_system_memory = True
            update_server_conf(server, 'system_memory', get_system_memory(memory_limit))

        # cpu
        if not server_config.get('cpu_count'):
            ret = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l")
            if ret and ret.stdout.strip().isdigit():
                cpu_num = int(ret.stdout)
                server_config['cpu_count'] = max(MIN_CPU_COUNT, int(cpu_num - 2))
            else:
                server_config['cpu_count'] = MIN_CPU_COUNT
            update_server_conf(server, 'cpu_count', server_config['cpu_count'])
        elif server_config['cpu_count'] < MIN_CPU_COUNT:
            update_server_conf(server, 'cpu_count', MIN_CPU_COUNT)
            stdio.warn('(%s): automatically adjust the cpu_count %s' % (server, MIN_CPU_COUNT))

        # disk
        if not server_config.get('datafile_size') and not user_server_config.get('datafile_disk_percentage'):
            disk = {'/': 0}
            ret = client.execute_command('df --block-size=1024')
            if ret:
                for total, used, avail, puse, path in re.findall('(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
                    disk[path] = {
                        'total': int(total) << 10,
                        'avail': int(avail) << 10,
                        'need': 0,
                    }
            for include_dir in dirs.values():
                while include_dir not in disk:
                    ret = client.execute_command('df --block-size=1024 %s' % include_dir)
                    if ret:
                        for total, used, avail, puse, path in re.findall('(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
                            disk[path] = {
                                'total': int(total) << 10,
                                'avail': int(avail) << 10,
                                'need': 0,
                            }
                        break
                    else:
                        include_dir = os.path.dirname(include_dir)
            mounts = {}
            for key in dirs:
                path = dirs[key]
                kp = '/'
                for p in disk:
                    if p in path:
                        if len(p) > len(kp):
                            kp = p
                mounts[path] = kp

            data_dir_mount = mounts[dirs['data_dir']]
            data_dir_disk = disk[data_dir_mount]

            clog_dir_mount = mounts[dirs['clog_dir']]
            clog_dir_disk = disk[clog_dir_mount]

            if clog_dir_mount == data_dir_mount:
                disk_free = data_dir_disk['avail']
                real_disk_total = data_dir_disk['total']
                if mounts[dirs['home_path']] == data_dir_mount:
                    if int(user_server_config.get('max_syslog_file_count', max_syslog_file_count_default)) != 0:
                        log_size = (256 << 20) * int(user_server_config.get('max_syslog_file_count', max_syslog_file_count_default)) * 4
                    else:
                        log_size = real_disk_total * 0.1
                else:
                    log_size = 0
                clog_padding_size = int(real_disk_total * (1 - clog_disk_utilization_threshold_max / 100.0 * 0.8))
                padding_size = clog_padding_size + log_size
                disk_total = real_disk_total - padding_size
                disk_used = real_disk_total - disk_free

                clog_disk_size = memory_limit * 4
                min_data_file_size = memory_limit * 3
                clog_size = int(round(clog_disk_size * 0.64))
                min_need = padding_size + clog_disk_size + min_data_file_size

                disk_flag = False
                if min_need > disk_free:
                    if auto_set_memory:
                        if auto_set_system_memory:
                            min_size = MIN_MEMORY * 7
                        else:
                            min_size = max(MIN_MEMORY, Capacity(user_server_config.get('system_memory')).bytes * 2) * 7
                        min_need = padding_size + min_size
                        if min_need <= disk_free:
                            memory_limit = (disk_free - padding_size) / 7
                            server_config['memory_limit'] = str(Capacity(memory_limit, 0))
                            update_server_conf(server, 'memory_limit', server_config['memory_limit'])
                            memory_limit = Capacity(server_config['memory_limit']).bytes
                            clog_disk_size = memory_limit * 4
                            clog_size = int(round(clog_disk_size * 0.64))
                            if auto_set_system_memory:
                                update_server_conf(server, 'system_memory', get_system_memory(memory_limit))
                            disk_flag = True
                else:
                    disk_flag = True

                if generate_check and not disk_flag:
                    stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s). Use `redo_dir` to set other disk for clog' % (ip, kp, Capacity(disk_free), Capacity(min_need)))
                    success = False
                    continue

                datafile_size_format = str(Capacity(disk_total - clog_disk_size - disk_used, 0))
                datafile_size = Capacity(datafile_size_format).bytes
                clog_disk_utilization_threshold = max(80, int(100.0 * (disk_used + datafile_size + padding_size + clog_disk_size * 0.8) / real_disk_total))
                clog_disk_utilization_threshold = min(clog_disk_utilization_threshold, clog_disk_utilization_threshold_max)
                clog_disk_usage_limit_percentage = min(int(clog_disk_utilization_threshold / 80.0 * 95), clog_disk_usage_limit_percentage_max)

                update_server_conf(server, 'datafile_size', datafile_size_format)
                update_server_conf(server, 'clog_disk_utilization_threshold', clog_disk_utilization_threshold)
                update_server_conf(server, 'clog_disk_usage_limit_percentage', clog_disk_usage_limit_percentage)
            else:
                datafile_size = max(5 << 30, data_dir_disk['avail'] * 0.8, 0)
                update_server_conf(server, 'datafile_size', Capacity(datafile_size, 0))
    if generate_password:
        generate_random_password(cluster_config)

    if generate_consistent_config:
        generate_global_config = generate_configs['global']
        server_num = len(cluster_config.servers)
        MIN_KEY = ['memory_limit', 'datafile_size', 'system_memory', 'cpu_count']
        MAX_KEY = ['clog_disk_utilization_threshold', 'clog_disk_usage_limit_percentage']
        CAPACITY_KEY = ['memory_limit', 'datafile_size', 'system_memory']
        keys = MIN_KEY + MAX_KEY
        for key in keys:
            servers = []
            values = []
            is_capacity_key = key in CAPACITY_KEY
            for server in cluster_config.servers:
                if key in generate_configs.get(server, {}):
                    value = generate_configs[server][key]
                    servers.append(server)
                    values.append(Capacity(value).bytes if is_capacity_key else value)
            if values:
                if len(values) != server_num and key in generate_global_config:
                    continue
                comp = min if key in MIN_KEY else max
                value = comp(values)
                generate_global_config[key] = str(Capacity(value, 0)) if is_capacity_key else value
                for server in servers:
                    del generate_configs[server][key]

    plugin_context.set_variable('success', success)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()