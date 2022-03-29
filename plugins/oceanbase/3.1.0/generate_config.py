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
        formate = '%.' + str(precision) + 'f%s'
        limit = 1024
    else:
        div = 1024
        limit = 1024
        formate = '%d%s'
    while idx < units_num and size >= limit:
        size /= div
        idx += 1
    return formate % (size, units[idx])


def get_system_memory(memory_limit):
    if memory_limit <= (64 << 30):
        system_memory = memory_limit * 0.5
    elif memory_limit <= (150 << 30):
        system_memory = memory_limit * 0.4
    else:
        system_memory = memory_limit * 0.3
    system_memory = max(4 << 30, system_memory)
    return format_size(system_memory, 0)


def generate_config(plugin_context, deploy_config, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    success = True
    stdio.start_loading('Generate observer configuration')

    if not cluster_config.get_global_conf().get('appname'):
        default_appname = 'obcluster'
        if 'obproxy' in deploy_config.components:
            obproxy_cluster_config = deploy_config.components['obproxy']
            cluster_name = obproxy_cluster_config.get_global_conf().get('cluster_name')
            if not cluster_name:
                for server in obproxy_cluster_config.servers:
                    server_config = obproxy_cluster_config.get_server_conf(server)
                    if server_config.get('cluster_name'):
                        default_appname = server_config['cluster_name']
                        break
        cluster_config.update_global_conf('appname', default_appname, False)

    MIN_MEMORY = 8 << 30
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

        max_syslog_file_count_default = 4
        if user_server_config.get('syslog_level') is None:
            cluster_config.update_server_conf(server, 'syslog_level', 'INFO', False)
        if user_server_config.get('enable_syslog_recycle') is None:
            cluster_config.update_server_conf(server, 'enable_syslog_recycle', True, False)
        if user_server_config.get('enable_syslog_wf') is None:
            cluster_config.update_server_conf(server, 'enable_syslog_wf', True, False)
        if user_server_config.get('max_syslog_file_count') is None:
            cluster_config.update_server_conf(server, 'max_syslog_file_count', max_syslog_file_count_default, False)
        if server_config.get('cluster_id') is None:
            cluster_config.update_server_conf(server, 'cluster_id', 1, False)

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
                    if memory_limit < MIN_MEMORY:
                        stdio.error(EC_OBSERVER_NOT_ENOUGH_MEMORY.format(ip=ip, free=format_size(free_memory), need=format_size(MIN_MEMORY)))
                        success = False
                        continue
                    memory_limit = max(MIN_MEMORY, memory_limit * 0.9)
                    server_config['memory_limit'] = format_size(memory_limit, 0)
                    cluster_config.update_server_conf(server, 'memory_limit', server_config['memory_limit'], False)
                else:
                    stdio.error("%s: fail to get memory info.\nPlease configure 'memory_limit' manually in configuration file")
                    success = False
                    continue
            else:
                try:
                    memory_limit = parse_size(server_config.get('memory_limit'))
                except:
                    stdio.error('memory_limit must be an integer')
                    return
            auto_set_memory = True

        auto_set_system_memory = False
        if not user_server_config.get('system_memory'):
            auto_set_system_memory = True
            cluster_config.update_server_conf(server, 'system_memory', get_system_memory(memory_limit), False)
            
        # cpu
        if not server_config.get('cpu_count'):
            ret = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l")
            if ret and ret.stdout.strip().isdigit():
                cpu_num = int(ret.stdout)
                server_config['cpu_count'] = max(16, int(cpu_num - 2))
            else:
                server_config['cpu_count'] = 16
        
        cluster_config.update_server_conf(server, 'cpu_count', max(16, server_config['cpu_count']), False)
            
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
                clog_disk_utilization_threshold_max = 95
                disk_free = data_dir_disk['avail']
                real_disk_total = data_dir_disk['total']
                if mounts[dirs['home_path']] == data_dir_mount:
                    if user_server_config.get('enable_syslog_recycle') is False:
                        log_size = real_disk_total * 0.1
                    else:
                        log_size = (256 << 20) * user_server_config.get('max_syslog_file_count', max_syslog_file_count_default) * 4
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
                            min_size = max(MIN_MEMORY, parse_size(user_server_config.get('system_memory')) * 2) * 7
                        min_need = padding_size + min_size
                        if min_need <= disk_free:
                            memory_limit = (disk_free - padding_size) / 7
                            server_config['memory_limit'] = format_size(memory_limit, 0)
                            cluster_config.update_server_conf(server, 'memory_limit', server_config['memory_limit'], False)
                            memory_limit = parse_size(server_config['memory_limit'])
                            clog_disk_size = memory_limit * 4
                            clog_size = int(round(clog_disk_size * 0.64))
                            if auto_set_system_memory:
                                cluster_config.update_server_conf(server, 'system_memory', get_system_memory(memory_limit), False)
                            disk_flag = True
                else:
                    disk_flag = True

                if not disk_flag:
                    stdio.error('(%s) %s not enough disk space. (Avail: %s, Need: %s). Use `redo_dir` to set other disk for clog' % (ip, kp, format_size(disk_free), format_size(min_need)))
                    success = False
                    continue

                datafile_size_format = format_size(disk_total - clog_disk_size - disk_used, 0)
                datafile_size = parse_size(datafile_size_format)
                clog_disk_utilization_threshold = max(80, int(100.0 * (disk_used + datafile_size + padding_size + clog_disk_size * 0.8) / real_disk_total))
                clog_disk_utilization_threshold = min(clog_disk_utilization_threshold, clog_disk_utilization_threshold_max)
                clog_disk_usage_limit_percentage = min(int(clog_disk_utilization_threshold / 80.0 * 95), 98)

                cluster_config.update_server_conf(server, 'datafile_size', datafile_size_format, False)
                cluster_config.update_server_conf(server, 'clog_disk_utilization_threshold', clog_disk_utilization_threshold, False)
                cluster_config.update_server_conf(server, 'clog_disk_usage_limit_percentage', clog_disk_usage_limit_percentage, False)
            else:
                datafile_size = max(5 << 30, data_dir_disk['avail'] * 0.8, 0)
                cluster_config.update_server_conf(server, 'datafile_size', format_size(datafile_size, 0), False)

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')