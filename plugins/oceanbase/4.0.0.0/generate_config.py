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

from _errno import EC_OBSERVER_NOT_ENOUGH_MEMORY


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'([1-9][0-9]*)\s*([B,K,M,G,T])', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G']
    units_num = len(units) - 1
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
        limit = 1024
    else:
        div = 1024
        limit = 1024
        format = '%d%s'
    while idx < units_num and size >= limit:
        size /= div
        idx += 1
    return format % (size, units[idx])


def get_system_memory(memory_limit):
    if memory_limit < (8 << 30):
        system_memory = 1 << 30
    elif memory_limit <= (64 << 30):
        system_memory = memory_limit * 0.5
    elif memory_limit <= (150 << 30):
        system_memory = memory_limit * 0.4
    else:
        system_memory = memory_limit * 0.3
    return max(1 << 30, system_memory)


def generate_config(plugin_context, deploy_config, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    success = True
    stdio.start_loading('Generate observer configuration')

    global_config = cluster_config.get_global_conf()
    if not global_config.get('appname'):
        default_appname = 'obcluster'
        for componet_name in ['obproxy', 'obproxy-ce']:
            if componet_name in deploy_config.components:
                obproxy_cluster_config = deploy_config.components[componet_name]
                cluster_name = obproxy_cluster_config.get_global_conf().get('cluster_name')
                if not cluster_name:
                    for server in obproxy_cluster_config.servers:
                        server_config = obproxy_cluster_config.get_server_conf(server)
                        if server_config.get('cluster_name'):
                            default_appname = server_config['cluster_name']
                            break
                break
        cluster_config.update_global_conf('appname', default_appname, False)

    max_syslog_file_count_default = 4
    if global_config.get('syslog_level') is None:
        cluster_config.update_global_conf('syslog_level', 'INFO', False)
    if global_config.get('enable_syslog_recycle') is None:
        cluster_config.update_global_conf('enable_syslog_recycle', True, False)
    if global_config.get('enable_syslog_wf') is None:
        cluster_config.update_global_conf('enable_syslog_wf', True, False)
    if global_config.get('max_syslog_file_count') is None:
        cluster_config.update_global_conf('max_syslog_file_count', max_syslog_file_count_default, False)
    if global_config.get('cluster_id') is None:
        cluster_config.update_global_conf('cluster_id', 1, False)

    MIN_MEMORY = 6 << 30
    PRO_MEMORY_MIN = 16 << 30
    SLOG_SIZE = 10 << 30
    MIN_CPU_COUNT = 16
    if getattr(plugin_context.options, 'mini', False):
        if not global_config.get('memory_limit_percentage') and not global_config.get('memory_limit'):
            cluster_config.update_global_conf('memory_limit', format_size(MIN_MEMORY, 0), False)
        if not global_config.get('datafile_size') and not global_config.get('datafile_disk_percentage'):
            cluster_config.update_global_conf('datafile_size', '20G', False)
        if not global_config.get('log_disk_size') and not global_config.get('log_disk_percentage'):
            cluster_config.update_global_conf('log_disk_size', '24G', False)

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        user_server_config = cluster_config.get_original_server_conf(server)
        if not server_config.get('home_path'):
            stdio.error("observer %s: missing configuration 'home_path' in configuration file" % server)
            success = False
            continue

        if user_server_config.get('devname') is None:
            if client.is_localhost():
                cluster_config.update_server_conf(server, 'devname', 'lo')
            else:
                devinfo = client.execute_command('cat /proc/net/dev').stdout
                interfaces = re.findall('\n\s+(\w+):', devinfo)
                for interface in interfaces:
                    if interface == 'lo':
                        continue
                    if client.execute_command('ping -W 1 -c 1 -I %s %s' % (interface, ip)):
                        cluster_config.update_server_conf(server, 'devname', interface)
                        break

        dirs = {"home_path": server_config['home_path']}
        dirs["data_dir"] = server_config['data_dir'] if server_config.get('data_dir') else os.path.join(server_config['home_path'], 'store')
        dirs["redo_dir"] = server_config['redo_dir'] if server_config.get('redo_dir') else dirs["data_dir"]
        dirs["clog_dir"] = server_config['clog_dir'] if server_config.get('clog_dir') else os.path.join(dirs["redo_dir"], 'clog')

        # memory
        auto_set_memory = False
        auto_set_system_memory = False
        system_memory = 0
        if user_server_config.get('system_memory'):
            system_memory = parse_size(user_server_config.get('system_memory'))
        min_memory = max(system_memory, MIN_MEMORY)
        if user_server_config.get('memory_limit_percentage'):
            ret = client.execute_command('cat /proc/meminfo')
            if ret:
                total_memory = 0
                for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                    if k == 'MemTotal':
                        total_memory = parse_size(str(v))
            memory_limit = int(total_memory * user_server_config.get('memory_limit_percentage') / 100)
        else:
            if not server_config.get('memory_limit'):
                ret = client.execute_command('cat /proc/meminfo')
                if ret:
                    free_memory = 0
                    for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
                        if k == 'MemAvailable':
                            free_memory = parse_size(str(v))
                    memory_limit = free_memory
                    if memory_limit < min_memory:
                        stdio.error(EC_OBSERVER_NOT_ENOUGH_MEMORY.format(ip=ip, free=format_size(free_memory), need=format_size(min_memory)))
                        success = False
                        continue
                    memory_limit = max(min_memory, memory_limit * 0.9)
                    server_config['memory_limit'] = format_size(memory_limit, 0)
                    cluster_config.update_server_conf(server, 'memory_limit', server_config['memory_limit'], False)
                else:
                    stdio.error("%s: fail to get memory info.\nPlease configure 'memory_limit' manually in configuration file")
                    success = False
                    continue
            else:
                try:
                    memory_limit = parse_size(server_config.get('memory_limit'))
                    auto_set_memory = True
                except:
                    stdio.error('memory_limit must be an integer')
                    return

        if system_memory == 0:
            auto_set_system_memory = True
            system_memory = get_system_memory(memory_limit)
            cluster_config.update_server_conf(server, 'system_memory', format_size(system_memory, 0), False)
            
        # cpu
        if not server_config.get('cpu_count'):
            ret = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l")
            if ret and ret.stdout.strip().isdigit():
                cpu_num = int(ret.stdout)
                server_config['cpu_count'] = max(MIN_CPU_COUNT, int(cpu_num - 2))
            else:
                server_config['cpu_count'] = MIN_CPU_COUNT
            cluster_config.update_server_conf(server, 'cpu_count', server_config['cpu_count'], False)
        elif server_config['cpu_count'] < MIN_CPU_COUNT:
            cluster_config.update_server_conf(server, 'cpu_count', MIN_CPU_COUNT, False)
            stdio.warn('(%s): automatically adjust the cpu_count %s' % (server, MIN_CPU_COUNT))
            
        # disk
        if (not server_config.get('datafile_size') and not user_server_config.get('datafile_disk_percentage')) or \
             (not server_config.get('log_disk_size') and not user_server_config.get('log_disk_percentage')):
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

            home_path_mount = mounts[dirs['home_path']]
            home_path_disk = disk[home_path_mount]
            
            data_dir_mount = mounts[dirs['data_dir']]
            data_dir_disk = disk[data_dir_mount]
            
            clog_dir_mount = mounts[dirs['clog_dir']]
            clog_dir_disk = disk[clog_dir_mount]

            auto_set_datafile_size = False
            auto_set_log_disk_size = False
            datafile_size = parse_size(server_config.get('datafile_size', 0))
            log_disk_size = parse_size(server_config.get('log_disk_size', 0))

            if not datafile_size:
                datafile_disk_percentage = int(user_server_config.get('datafile_disk_percentage', 0))
                if datafile_disk_percentage:
                    datafile_size = data_dir_mount['total'] * datafile_disk_percentage / 100
                else:
                    auto_set_datafile_size = True

            if not log_disk_size:
                log_disk_percentage = int(user_server_config.get('log_disk_percentage', 0))
                if log_disk_percentage:
                    log_disk_size = clog_dir_disk['total'] * log_disk_percentage / 100
                else:
                    auto_set_log_disk_size = True

            if user_server_config.get('enable_syslog_recycle') is False:
                log_size = 1 << 30 # 默认先给1G普通日志空间
            else:
                log_size = (256 << 20) * user_server_config.get('max_syslog_file_count', max_syslog_file_count_default) * 4

            if clog_dir_mount == data_dir_mount:
                min_log_size = log_size if clog_dir_mount == home_path_mount else 0
                MIN_NEED = min_log_size + SLOG_SIZE
                if auto_set_datafile_size:
                    min_datafile_size = memory_limit * 3
                    MIN_NEED += min_memory * 3
                else:
                    min_datafile_size = datafile_size
                    MIN_NEED += datafile_size
                if auto_set_log_disk_size:
                    min_log_disk_size = memory_limit * 3
                    MIN_NEED += min_memory * 3
                else:
                    min_log_disk_size = log_disk_size
                    MIN_NEED += log_disk_size
                min_need = min_log_size + min_datafile_size + min_log_disk_size
                
                disk_free = data_dir_disk['avail']
                if MIN_NEED > disk_free:
                    stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s).' % (ip, data_dir_mount, format_size(disk_free), format_size(MIN_NEED)))
                    success = False
                    continue
                if min_need > disk_free:
                    if not auto_set_memory:
                        stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s).' % (ip, data_dir_mount, format_size(disk_free), format_size(min_need)))
                        success = False
                        continue
                    
                    disk_free = disk_free - log_size - SLOG_SIZE
                    memory_factor = 0
                    if auto_set_datafile_size is False:
                        disk_free -= min_datafile_size
                        memory_factor += 3
                    if auto_set_log_disk_size is False:
                        disk_free -= min_log_disk_size
                        memory_factor += 3
                    memory_limit = format_size(disk_free / memory_factor, 0)
                    cluster_config.update_server_conf(server, 'memory_limit', memory_limit, False)
                    memory_limit = parse_size(memory_limit)
                    if auto_set_system_memory:
                        system_memory = get_system_memory(memory_limit)
                        cluster_config.update_server_conf(server, 'system_memory', format_size(system_memory, 0), False)
                    log_disk_size = memory_limit * 3
                    datafile_size = disk_free - log_disk_size
                else:
                    log_disk_size = memory_limit * 3
                    datafile_size = disk_free - log_size - SLOG_SIZE - log_disk_size

                if auto_set_datafile_size:
                    cluster_config.update_server_conf(server, 'datafile_size', format_size(datafile_size, 0), False)
                if auto_set_log_disk_size:
                    cluster_config.update_server_conf(server, 'log_disk_size', format_size(log_disk_size, 0), False)
            else:
                datafile_min_memory_limit = memory_limit
                if auto_set_datafile_size:
                    datafile_size = 3 * memory_limit
                    min_log_size = log_size if data_dir_mount == home_path_mount else 0
                    disk_free = data_dir_disk['avail']
                    min_need = min_log_size + datafile_size + SLOG_SIZE
                    if min_need > disk_free:
                        if not auto_set_memory:
                            stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s).' % (ip, data_dir_mount, format_size(disk_free), format_size(min_need)))
                            success = False
                            continue
                        datafile_min_memory_limit = (disk_free - log_size - SLOG_SIZE) / 3
                        if datafile_min_memory_limit < min_memory:
                            stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s).' % (ip, data_dir_mount, format_size(disk_free), format_size(min_need)))
                            success = False
                            continue
                        datafile_min_memory_limit = parse_size(format_size(datafile_min_memory_limit, 0))
                        disk_log_size = datafile_min_memory_limit * 3

                log_disk_min_memory_limit = memory_limit
                if auto_set_log_disk_size:
                    log_disk_size = 3 * memory_limit
                    min_log_size = log_size if clog_dir_mount == home_path_mount else 0
                    disk_free = clog_dir_disk['avail']
                    min_need = min_log_size + log_disk_size
                    if min_need > disk_free:
                        if not auto_set_memory:
                            stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s).' % (ip, clog_dir_mount, format_size(disk_free), format_size(min_need)))
                            success = False
                            continue
                        log_disk_min_memory_limit = (disk_free - log_size) / 3
                        if log_disk_min_memory_limit < min_memory:
                            stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s).' % (ip, clog_dir_mount, format_size(disk_free), format_size(min_need)))
                            success = False
                            continue
                        log_disk_min_memory_limit = parse_size(format_size(log_disk_min_memory_limit, 0))
                        log_disk_size = log_disk_min_memory_limit * 3
                
                if auto_set_memory:
                    cluster_config.update_server_conf(server, 'memory_limit', format_size(memory_limit, 0), False)
                    if auto_set_system_memory:
                        system_memory = get_system_memory(memory_limit)
                        cluster_config.update_server_conf(server, 'system_memory', format_size(system_memory, 0), False)
                
                if auto_set_datafile_size:
                    cluster_config.update_server_conf(server, 'datafile_size', format_size(datafile_size, 0), False)
                if auto_set_log_disk_size:
                    cluster_config.update_server_conf(server, 'log_disk_size', format_size(log_disk_size, 0), False)

        if memory_limit < PRO_MEMORY_MIN:
            cluster_config.update_server_conf(server, 'production_mode', False, False)
                        
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')