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

from _errno import EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE, EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED, EC_OBSERVER_GET_MEMINFO_FAIL
import _errno as err
from tool import ConfigUtil
from _types import Capacity


def get_system_memory(memory_limit):
    if memory_limit < 12 << 30:
        system_memory = 1 << 30
    elif memory_limit < 20 << 30:
        system_memory = 5 << 30
    elif memory_limit < 40 << 30:
        system_memory = 6 << 30
    elif memory_limit < 60 << 30:
        system_memory = 7 << 30
    elif memory_limit < 80 << 30:
        system_memory = 8 << 30
    elif memory_limit < 100 << 30:
        system_memory = 9 << 30
    elif memory_limit < 130 << 30:
        system_memory = 10 << 30
    else:
        system_memory = int(memory_limit * 0.08)
    return system_memory


def generate_config(plugin_context, generate_config_mini=False, auto_depend=False, generate_check=True, return_generate_keys=False, generate_consistent_config=False, only_generate_password=False, generate_password=True, *args, **kwargs):
    if return_generate_keys:
        generate_keys = []
        if not only_generate_password:
            generate_keys += [
                'memory_limit', 'datafile_size', 'log_disk_size', 'system_memory', 'cpu_count', 'production_mode',
                'syslog_level', 'enable_syslog_wf', 'max_syslog_file_count', 'cluster_id', 'ocp_meta_tenant_log_disk_size',
                'datafile_next', 'datafile_maxsize'
            ]
        if generate_password:
            generate_keys += ['root_password', 'proxyro_password', 'ocp_meta_password', 'ocp_agent_monitor_password']
        return plugin_context.return_true(generate_keys=generate_keys)
    
    cluster_config = plugin_context.cluster_config
    original_global_conf = cluster_config.get_original_global_conf()
    if not original_global_conf.get('appname'):
        cluster_config.update_global_conf('appname', plugin_context.deploy_name)
    if original_global_conf.get('cluster_id') is None:
        cluster_config.update_global_conf('cluster_id', round(time.time()) % 4294901759, False)
    if generate_password or only_generate_password:
        generate_random_password(cluster_config, auto_depend)
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
    added_components = cluster_config.get_deploy_added_components()
    be_depend = cluster_config.be_depends
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate observer configuration')

    global_config = cluster_config.get_global_conf()
    max_syslog_file_count_default = 4
    if global_config.get('enable_syslog_wf') is None:
        update_global_conf('enable_syslog_wf', False)
    if global_config.get('max_syslog_file_count') is None:
        update_global_conf('max_syslog_file_count', max_syslog_file_count_default)

    MIN_MEMORY = 6 << 30
    PRO_MEMORY_MIN = 16 << 30
    SLOG_SIZE = 4 << 30
    MIN_CPU_COUNT = 16
    START_NEED_MEMORY = 3 << 30

    MINI_MEMORY_SIZE = MIN_MEMORY
    MINI_DATA_FILE_SIZE = 2 << 30
    MINI_DATA_FILE_NEXT = 2 << 30
    MINI_DATA_FILE_MAX_SIZE = 8 << 30
    MINI_LOG_DISK_SIZE = 14 << 30

    DATA_RESERVED = 0.95
    DATA_NEXT = 0.1

    has_ocp = 'ocp-express' in added_components and 'ocp-express' in be_depend
    if any([key in global_config for key in ["ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password"]]):
        has_ocp = True
    ip_server_memory_info = {}
    servers_info = {}
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        user_server_config = cluster_config.get_original_server_conf_with_global(server, format_conf=True)

        dirs = {"home_path": server_config['home_path']}
        dirs["data_dir"] = server_config['data_dir'] if server_config.get('data_dir') else os.path.join(server_config['home_path'], 'store')
        dirs["redo_dir"] = server_config['redo_dir'] if server_config.get('redo_dir') else dirs["data_dir"]
        dirs["clog_dir"] = server_config['clog_dir'] if server_config.get('clog_dir') else os.path.join(dirs["redo_dir"], 'clog')

        # memory
        auto_set_memory = False
        auto_set_system_memory = False
        auto_set_min_pool_memory = False
        system_memory = 0
        if user_server_config.get('system_memory'):
            system_memory = Capacity(user_server_config.get('system_memory')).bytes
        if generate_config_mini and '__min_full_resource_pool_memory' not in user_server_config:
            auto_set_min_pool_memory = True
        min_pool_memory = server_config['__min_full_resource_pool_memory']
        min_memory = max(system_memory, MIN_MEMORY)
        if ip not in ip_server_memory_info:
            ret = client.execute_command('cat /proc/meminfo')
            if ret:
                ip_server_memory_info[ip] = server_memory_stats = {}
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

        if user_server_config.get('memory_limit_percentage'):
            if ip in ip_server_memory_info:
                total_memory = Capacity(ip_server_memory_info[ip]['total']).bytes
                memory_limit = int(total_memory * user_server_config.get('memory_limit_percentage') / 100)
            elif generate_check:
                stdio.error(EC_OBSERVER_GET_MEMINFO_FAIL.format(server=server))
                success = False
                continue
            else:
                memory_limit = MIN_MEMORY
        elif not server_config.get('memory_limit'):
            if generate_config_mini:
                memory_limit = MINI_MEMORY_SIZE
                update_server_conf(server, 'memory_limit', str(Capacity(memory_limit, 0)))
                update_server_conf(server, 'production_mode', False)
                if auto_set_min_pool_memory:
                    min_pool_memory = 1073741824
                    update_server_conf(server, '__min_full_resource_pool_memory', min_pool_memory)
            else:
                if ip in ip_server_memory_info:
                    server_memory_stats = ip_server_memory_info[ip]
                    if generate_check:
                        if server_memory_stats['available'] < START_NEED_MEMORY:
                            stdio.error(EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE.format(ip=ip, available=str(Capacity(server_memory_stats['available'])), need=str(Capacity(START_NEED_MEMORY))))
                            success = False
                            continue

                        if server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached'] < MIN_MEMORY:
                            stdio.error(EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=str(Capacity(server_memory_stats['free'])), cached=str(Capacity(server_memory_stats['buffers'] + server_memory_stats['cached'])), need=str(Capacity(MIN_MEMORY))))
                            success = False
                            continue
                    memory_limit = max(MIN_MEMORY, int(int(server_memory_stats['available'] * 0.9)))
                    update_server_conf(server, 'memory_limit', str(Capacity(memory_limit, 0)))
                    auto_set_memory = True
                elif generate_check:
                    stdio.error(EC_OBSERVER_GET_MEMINFO_FAIL.format(server=server))
                    success = False
                    continue
                else:
                    memory_limit = MIN_MEMORY
        else:
            memory_limit = Capacity(server_config.get('memory_limit')).bytes

        if system_memory == 0:
            auto_set_system_memory = True
            system_memory = get_system_memory(memory_limit)
            update_server_conf(server, 'system_memory', str(Capacity(system_memory, 0)))

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
        datafile_size = server_config.get('datafile_size', 0)
        if datafile_size:
            datafile_size = Capacity(user_server_config.get('datafile_size')).bytes
        log_disk_size = server_config.get('log_disk_size', 0)
        if log_disk_size:
            log_disk_size = Capacity(user_server_config.get('log_disk_size')).bytes
        if not server_config.get('datafile_size') or not server_config.get('log_disk_size'):
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

            if not datafile_size:
                datafile_disk_percentage = int(user_server_config.get('datafile_disk_percentage', 0))
                if datafile_disk_percentage:
                    datafile_size = data_dir_disk['total'] * datafile_disk_percentage / 100
                elif generate_config_mini:
                    datafile_size = MINI_DATA_FILE_SIZE
                    update_server_conf(server, 'datafile_size', str(Capacity(datafile_size, 0)))
                    if 'datafile_maxsize' not in user_server_config:
                        update_server_conf(server, 'datafile_maxsize', str(Capacity(MINI_DATA_FILE_MAX_SIZE, 0)))
                    if 'datafile_next' not in user_server_config:
                        update_server_conf(server, 'datafile_next', str(Capacity(MINI_DATA_FILE_NEXT, 0)))

                else:
                    auto_set_datafile_size = True

            if not log_disk_size:
                log_disk_percentage = int(user_server_config.get('log_disk_percentage', 0))
                if log_disk_percentage:
                    log_disk_size = int(clog_dir_disk['total'] * log_disk_percentage / 100)
                elif generate_config_mini:
                    log_disk_size = MINI_LOG_DISK_SIZE
                    update_server_conf(server, 'log_disk_size', str(Capacity(log_disk_size, 0)))
                else:
                    auto_set_log_disk_size = True

            if int(user_server_config.get('max_syslog_file_count', max_syslog_file_count_default)) != 0:
                log_size = (256 << 20) * int(user_server_config.get('max_syslog_file_count', max_syslog_file_count_default)) * 4
            else:
                log_size = 1 << 30  # 默认先给1G普通日志空间

            datafile_maxsize = datafile_next = 0
            if user_server_config.get('datafile_maxsize'):
                datafile_maxsize = Capacity(user_server_config.get('datafile_maxsize')).bytes
            if clog_dir_mount == data_dir_mount:
                min_log_size = log_size if clog_dir_mount == home_path_mount else 0
                MIN_NEED = min_log_size + SLOG_SIZE
                if auto_set_datafile_size:
                    datafile_size =min_datafile_size = MINI_DATA_FILE_SIZE
                else:
                    min_datafile_size = datafile_size
                MIN_NEED += Capacity(min_datafile_size).bytes
                if auto_set_log_disk_size:
                    log_disk_size = min_log_disk_size = (memory_limit - system_memory) * 3 + system_memory
                else:
                    min_log_disk_size = log_disk_size
                MIN_NEED += Capacity(min_log_disk_size).bytes
                min_need = min_log_size + Capacity(min_datafile_size).bytes + Capacity(min_log_disk_size).bytes

                disk_free = data_dir_disk['avail']
                if MIN_NEED > disk_free:
                    if generate_check:
                        stdio.error(err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=data_dir_mount, avail=str(Capacity(disk_free)), need=str(Capacity(MIN_NEED))))
                        success = False
                        continue
                    else:
                        if auto_set_memory:
                            memory_limit = MIN_MEMORY
                            update_server_conf(server, 'memory_limit', str(Capacity(memory_limit, 0)))
                        if auto_set_system_memory:
                            system_memory = get_system_memory(memory_limit)
                            update_server_conf(server, 'system_memory', str(Capacity(system_memory, 0)))
                        if auto_set_datafile_size:
                            datafile_size = MINI_DATA_FILE_SIZE
                        if auto_set_log_disk_size:
                            log_disk_size = (memory_limit - system_memory) * 3 + system_memory
                elif min_need > disk_free:
                    if generate_check and not auto_set_memory:
                        stdio.error(err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=data_dir_mount, avail=str(Capacity(disk_free)), need=str(Capacity(min_need))))
                        success = False
                        continue

                    disk_free = disk_free - log_size - SLOG_SIZE
                    memory_factor = 6
                    if auto_set_datafile_size is False:
                        disk_free -= min_datafile_size
                        memory_factor -= 3
                    if auto_set_log_disk_size is False:
                        disk_free -= min_log_disk_size
                        memory_factor -= 3
                    memory_limit = str(Capacity(disk_free / max(1, memory_factor), 0))
                    update_server_conf(server, 'memory_limit', memory_limit)
                    memory_limit = Capacity(memory_limit).bytes
                    if auto_set_system_memory:
                        system_memory = get_system_memory(memory_limit)
                        update_server_conf(server, 'system_memory', str(Capacity(system_memory, 0)))
                    if auto_set_log_disk_size:
                        log_disk_size = (memory_limit - system_memory) * 3 + system_memory
                    if auto_set_datafile_size:
                        datafile_size = min(disk_free - log_disk_size, (memory_limit - system_memory) * 3 + system_memory)
                        if not datafile_maxsize:
                            datafile_maxsize = max(disk_free - log_disk_size, (memory_limit - system_memory) * 3 + system_memory)
                else:
                    if auto_set_log_disk_size:
                        log_disk_size = (memory_limit - system_memory) * 3 + system_memory
                    if auto_set_datafile_size:
                        datafile_size = min((disk_free - log_size - SLOG_SIZE - log_disk_size) * DATA_RESERVED, (memory_limit - system_memory) * 3 + system_memory)
                        if not datafile_maxsize:
                            datafile_maxsize = max((disk_free - log_size - SLOG_SIZE - log_disk_size) * DATA_RESERVED, (memory_limit - system_memory) * 3 + system_memory)

                if auto_set_datafile_size:
                    datafile_next = max(MINI_DATA_FILE_NEXT, DATA_NEXT * datafile_maxsize)
                    datafile_size = min(datafile_maxsize, datafile_size)
                    update_server_conf(server, 'datafile_size', str(Capacity(datafile_size, 0)))
                    if datafile_maxsize > datafile_size:
                        if 'datafile_maxsize' not in user_server_config:
                            update_server_conf(server, 'datafile_maxsize', str(Capacity(datafile_maxsize, 0)))
                        if 'datafile_next' not in user_server_config:
                            update_server_conf(server, 'datafile_next', str(Capacity(datafile_next, 0)))
                if auto_set_log_disk_size:
                    update_server_conf(server, 'log_disk_size', str(Capacity(log_disk_size, 0)))
            else:
                datafile_min_memory_limit = memory_limit
                if auto_set_datafile_size:
                    datafile_size = 3 * datafile_min_memory_limit
                    min_log_size = log_size if data_dir_mount == home_path_mount else 0
                    disk_free = data_dir_disk['avail']
                    min_need = min_log_size + datafile_size + SLOG_SIZE

                    if generate_check and min_need > disk_free:
                        if not auto_set_memory:
                            stdio.error(err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=data_dir_mount, avail=str(Capacity(disk_free)), need=str(Capacity(min_need))))
                            success = False
                            continue
                        datafile_min_memory_limit = (disk_free - min_log_size - SLOG_SIZE) / 3
                        if datafile_min_memory_limit < min_memory:
                            stdio.error(err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=data_dir_mount, avail=str(Capacity(disk_free)), need=str(Capacity(min_need))))
                            success = False
                            continue
                        datafile_min_memory_limit = Capacity(str(Capacity(datafile_min_memory_limit, 0))).bytes
                        datafile_size = datafile_min_memory_limit * 3
                    if datafile_maxsize:
                        datafile_size = min(datafile_size, datafile_maxsize)
                    else:
                        datafile_maxsize = (disk_free - min_log_size - SLOG_SIZE) * DATA_RESERVED
                    datafile_next = DATA_NEXT * datafile_maxsize

                log_disk_min_memory_limit = memory_limit
                if auto_set_log_disk_size:
                    log_disk_size = (memory_limit - system_memory) * 3 + system_memory
                    min_log_size = log_size if clog_dir_mount == home_path_mount else 0
                    disk_free = clog_dir_disk['avail']
                    min_need = min_log_size + log_disk_size
                    if generate_check and min_need > disk_free:
                        if not auto_set_memory:
                            stdio.error(err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=data_dir_mount, avail=str(Capacity(disk_free)), need=str(Capacity(min_need))))
                            success = False
                            continue
                        log_disk_min_memory_limit = (disk_free - log_size) / 3
                        if log_disk_min_memory_limit < min_memory:
                            stdio.error(err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=data_dir_mount, avail=str(Capacity(disk_free)), need=str(Capacity(min_need))))
                            success = False
                            continue
                        log_disk_min_memory_limit = Capacity(str(Capacity(log_disk_min_memory_limit, 0))).bytes
                        log_disk_size = log_disk_min_memory_limit * 3

                if auto_set_memory:
                    update_server_conf(server, 'memory_limit', str(Capacity(memory_limit, 0)))
                    if auto_set_system_memory:
                        system_memory = get_system_memory(memory_limit)
                        update_server_conf(server, 'system_memory', system_memory)

                if auto_set_datafile_size:
                    update_server_conf(server, 'datafile_size', str(Capacity(datafile_size, 0)))
                    if datafile_maxsize > datafile_size:
                        if 'datafile_maxsize' not in user_server_config:
                            update_server_conf(server, 'datafile_maxsize', str(Capacity(datafile_maxsize, 0)))
                        if 'datafile_next' not in user_server_config:
                            update_server_conf(server, 'datafile_next', str(Capacity(datafile_next, 0)))
                if auto_set_log_disk_size:
                    update_server_conf(server, 'log_disk_size', str(Capacity(log_disk_size, 0)))

        if memory_limit < PRO_MEMORY_MIN:
            update_server_conf(server, 'production_mode', False)
        servers_info[server] = {
            "memory_limit": memory_limit,
            "system_memory": system_memory,
            "min_pool_memory": min_pool_memory,
            "log_disk_size": log_disk_size
        }

    # ocp meta db
    SYS_TENANT_LOG_DISK_SCALE = 1
    if has_ocp:
        if 'ocp_meta_tenant_log_disk_size' not in global_config and 'log_disk_size' not in global_config.get('ocp_meta_tenant', {}):
            if generate_config_mini:
                update_global_conf('ocp_meta_tenant_log_disk_size', '6656M')
            else:
                meta_min_log_disk_size = 6 << 30
                expect_log_disk_size = (9 * 512 + 512 * len(cluster_config.servers) + 512 * 3) << 20
                max_available = 0
                sys_memory_size = None
                sys_log_disk_size = None
                if 'sys_tenant' in global_config:
                    if 'memory_size' in global_config['sys_tenant']:
                        sys_memory_size = global_config['sys_tenant']['memory_size']
                    if 'log_disk_size' in global_config['sys_tenant']:
                        sys_log_disk_size = global_config['sys_tenant']['log_disk_size']
                for server in cluster_config.servers:
                    # server_config = cluster_config.get_server_conf_with_default(server)
                    server_info = servers_info.get(server)
                    if not server_info:
                        continue
                    memory_limit = Capacity(server_info['memory_limit']).bytes
                    system_memory = Capacity(server_info['system_memory']).bytes
                    log_disk_size = Capacity(server_info['log_disk_size']).bytes
                    min_pool_memory = Capacity(server_info['min_pool_memory']).bytes
                    if not sys_log_disk_size:
                        if not sys_memory_size:
                            sys_memory_size = max(min_pool_memory, min(int((memory_limit - system_memory) * 0.25), 16 << 30))
                        sys_log_disk_size = sys_memory_size * SYS_TENANT_LOG_DISK_SCALE
                    max_available = max(max_available, log_disk_size - sys_log_disk_size)
                if expect_log_disk_size > max_available:
                    expect_log_disk_size = meta_min_log_disk_size
                if expect_log_disk_size > max_available and generate_check:
                    stdio.error(err.EC_OCP_EXPRESS_META_DB_NOT_ENOUGH_LOG_DISK_AVAILABLE.format(avail=max_available, need=expect_log_disk_size))
                    success = False
                cluster_config.update_global_conf('ocp_meta_tenant_log_disk_size', str(Capacity(expect_log_disk_size, 0)), False)
        if generate_config_mini and 'ocp_meta_tenant_memory_size' not in global_config and 'memory_size' not in global_config.get('ocp_meta_tenant', {}):
            update_global_conf('ocp_meta_tenant_memory_size', '1536M')

    if generate_password:
        generate_random_password(cluster_config, auto_depend)

    if generate_consistent_config:
        generate_global_config = generate_configs['global']
        server_num = len(cluster_config.servers)
        keys = ['memory_limit', 'datafile_size', 'system_memory', 'log_disk_size', 'cpu_count', 'production_mode']
        for key in keys:
            servers = []
            values = []
            is_capacity_key = (key != 'cpu_count' and key != 'production_mode')
            for server in cluster_config.servers:
                if key in generate_configs.get(server, {}):
                    value = generate_configs[server][key]
                    servers.append(server)
                    values.append(Capacity(value).bytes if is_capacity_key else value)
            if values:
                if len(values) != server_num and key in generate_global_config:
                    continue
                value = min(values)
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


def generate_random_password(cluster_config, auto_depend):
    add_components = cluster_config.get_deploy_added_components()
    be_depend = cluster_config.be_depends
    global_config = cluster_config.get_original_global_conf()
    be_depends = {
        component: (auto_depend or component in be_depend)
        for component in ['obagent', 'obproxy', 'obproxy-ce', 'oblogproxy', 'ocp-express']
    }
    added_components = {
        component: component in add_components
        for component in ['oceanbase', 'oceanbase-ce', 'obagent', 'obproxy', 'obproxy-ce', 'oblogproxy', 'ocp-express']
    }

    if added_components[cluster_config.name] and 'root_password' not in global_config:
        cluster_config.update_global_conf('root_password', ConfigUtil.get_random_pwd_by_total_length(20), False)

    if added_components['obagent'] and be_depends['obagent'] and 'ocp_agent_monitor_password' not in global_config:
        cluster_config.update_global_conf('ocp_agent_monitor_password', ConfigUtil.get_random_pwd_by_total_length(), False)

    if 'proxyro_password' not in global_config:
        for component_name in ['obproxy', 'obproxy-ce']:
            if added_components[component_name] and be_depends[component_name]:
                cluster_config.update_global_conf('proxyro_password', ConfigUtil.get_random_pwd_by_total_length(), False)

    if (added_components['ocp-express'] and be_depends['ocp-express'] and 'ocp_meta_password' not in global_config) or \
          any([key in global_config for key in ["ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password"]]):
            if 'ocp_root_password' not in global_config:
                cluster_config.update_global_conf('ocp_root_password', ConfigUtil.get_random_pwd_by_total_length(), False) # 不支持在配置文件中中配置
            if 'ocp_meta_password' not in global_config :
                cluster_config.update_global_conf('ocp_meta_password', ConfigUtil.get_random_pwd_by_total_length(), False)
