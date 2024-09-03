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


import re, os
import time

from _errno import EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE, EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED
from tool import ConfigUtil
from _types import Capacity


def get_system_memory(memory_limit):
    if memory_limit <= (64 << 30):
        system_memory = memory_limit * 0.5
    elif memory_limit <= (150 << 30):
        system_memory = memory_limit * 0.4
    else:
        system_memory = memory_limit * 0.3
    system_memory = max(4 << 30, system_memory)
    return str(Capacity(system_memory, 0))


def generate_config(plugin_context, generate_config_mini=False, auto_depend=False, generate_check=True, return_generate_keys=False, generate_consistent_config=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if not only_generate_password:
            generate_keys += [
                'memory_limit', 'datafile_size', 'clog_disk_utilization_threshold', 'clog_disk_usage_limit_percentage',
                'syslog_level', 'enable_syslog_wf', 'max_syslog_file_count', 'cluster_id',
                'devname', 'system_memory', 'cpu_count'
            ]
        if generate_password:
            generate_keys += ['root_password', 'proxyro_password']
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    original_global_conf = cluster_config.get_original_global_conf()
    if not original_global_conf.get('appname'):
        cluster_config.update_global_conf('appname', plugin_context.deploy_name)
    if original_global_conf.get('cluster_id') is None:
        cluster_config.update_global_conf('cluster_id', round(time.time()) % 4294901759, False)
    if generate_password or only_generate_password:
        generate_random_password(cluster_config)
    if only_generate_password:
        return plugin_context.return_true()

    def update_server_conf(server, key, value):
        if server not in generate_configs:
            generate_configs[server] = {}
        generate_configs[server][key] = value
    def update_global_conf(key, value):
        generate_configs['global'][key] = value

    def summit_config():
        generate_global_config = generate_configs['global']
        for key in generate_global_config:
            stdio.verbose('Update global config %s to %s' % (key, generate_global_config[key]))
            cluster_config.update_global_conf(key, generate_global_config[key], False)
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_server_config = generate_configs[server]
            for key in generate_server_config:
                stdio.verbose('Update server %s config %s to %s' % (server, key, generate_server_config[key]))
                cluster_config.update_server_conf(server, key, generate_server_config[key], False)

    clients = plugin_context.clients
    stdio = plugin_context.stdio
    success = True
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate observer configuration')

    MIN_MEMORY = 8 << 30
    MIN_CPU_COUNT = 16
    START_NEED_MEMORY = 3 << 30
    clog_disk_utilization_threshold_max = 95
    clog_disk_usage_limit_percentage_max = 98
    global_config = cluster_config.get_original_global_conf()

    max_syslog_file_count_default = 4
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

    # merge_generate_config
    merge_config = {}
    generate_global_config = generate_configs['global']
    count_base = len(cluster_config.servers) - 1
    if count_base < 1:
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_global_config.update(generate_configs[server])
            generate_configs[server] = {}
    else:
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_server_config = generate_configs[server]
            merged_server_config = {}
            for key in generate_server_config:
                if key in generate_global_config:
                    if generate_global_config[key] != generate_server_config[key]:
                        merged_server_config[key] = generate_server_config[key]
                elif key in merge_config:
                    if merge_config[key]['value'] != generate_server_config[key]:
                        merged_server_config[key] = generate_server_config[key]
                    elif count_base == merge_config[key]['count']:
                        generate_global_config[key] = generate_server_config[key]
                        del merge_config[key]
                    else:
                        merge_config[key]['severs'].append(server)
                        merge_config[key]['count'] += 1
                else:
                    merge_config[key] = {'value': generate_server_config[key], 'severs': [server], 'count': 1}
            generate_configs[server] = merged_server_config

        for key in merge_config:
            config_st = merge_config[key]
            for server in config_st['severs']:
                if server not in generate_configs:
                    continue
                generate_server_config = generate_configs[server]
                generate_server_config[key] = config_st['value']

    # summit_config
    summit_config()

    if auto_depend and 'ob-configserver' in plugin_context.components:
        cluster_config.add_depend_component('ob-configserver')

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    be_depend = cluster_config.be_depends
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'root_password' not in global_config:
        cluster_config.update_global_conf('root_password', ConfigUtil.get_random_pwd_by_total_length(20), False)

    if 'proxyro_password' not in global_config:
        for component_name in ['obproxy', 'obproxy-ce']:
            if component_name in add_components and component_name in be_depend:
                cluster_config.update_global_conf('proxyro_password', ConfigUtil.get_random_pwd_by_total_length(), False)