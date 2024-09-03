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
import socket
import sys
import copy
from math import sqrt

import _errno as err
from _types import Capacity


stdio = None
success = True
production_mode = False

def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{if($4==\"0A\") print $2,$4,$10}' | grep ':%s' | awk -F' ' '{print $3}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def time_delta(client):
    time_st = time.time() * 1000
    time_srv = int(client.execute_command('date +%s%N').stdout) / 1000000
    time_ed = time.time() * 1000

    time_it = time_ed - time_st
    time_srv -= time_it/2
    return time_srv - time_st


def get_mount_path(disk, _path):
    _mount_path = '/'
    for p in disk:
        if p in _path and _path.startswith(p):
            if len(p) > len(_mount_path):
                _mount_path = p
    return _mount_path


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

def has_obshell(repository):
    repository_dir = repository.repository_dir
    obshell_path = os.path.join(repository_dir, 'bin', 'obshell')
    return os.path.exists(obshell_path)

def start_check(plugin_context, init_check_status=False, strict_check=False, work_dir_check=False, work_dir_empty_check=True, generate_configs={}, precheck=False, source_option='start', *args, **kwargs):
    def check_pass(item):
        status = check_status[server]
        if status[item].status == err.CheckStatus.WAIT:
            status[item].status = err.CheckStatus.PASS
    def check_fail(item, error, suggests=[]):
        status = check_status[server][item]
        if status.status == err.CheckStatus.WAIT:
            status.error = error
            status.suggests = suggests
            status.status = err.CheckStatus.FAIL
    def wait_2_pass():
        status = check_status[server]
        for item in status:
            check_pass(item)
    def alert(item, error, suggests=[]):
        global success
        if strict_check:
            success = False
            check_fail(item, error, suggests)
            print_with_suggests(error, suggests)
        else:
            stdio.warn(error)

    def alert_strict(item, error, suggests=[]):
        global success
        if strict_check or production_mode:
            success = False
            check_fail(item, error, suggests)
            print_with_suggests(error, suggests)
        else:
            stdio.warn(error)

    def error(item, _error, suggests=[]):
        global success
        if plugin_context.dev_mode:
            stdio.warn(_error)
        else:
            success = False
            check_fail(item, _error, suggests)
            print_with_suggests(_error, suggests)

    def critical(item, error, suggests=[]):
        global success
        success = False
        check_fail(item, error, suggests)
        print_with_suggests(error, suggests)

    def print_with_suggests(error, suggests=[]):
        stdio.error('{}, {}'.format(error, suggests[0].msg if suggests else ''))

    def system_memory_check():
        server_memory_config = server_memory_stat['servers']
        for server in server_memory_config:
            if server_memory_config[server]['system_memory']:
                memory_limit = server_memory_config[server]['num']
                if not memory_limit:
                    server_memory_config[server]['num'] = memory_limit = server_memory_config[server]['percentage'] * server_memory_stats['total']
                factor = 0.75
                suggest = err.SUG_OBSERVER_SYS_MEM_TOO_LARGE.format(factor=factor)
                suggest.auto_fix = 'system_memory' not in global_generate_config and 'system_memory' not in generate_configs.get(server, {})
                if memory_limit <= server_memory_config[server]['system_memory']:
                    critical('mem', err.EC_OBSERVER_SYS_MEM_TOO_LARGE.format(server=server), [suggest])
                elif memory_limit * factor < server_memory_config[server]['system_memory']:
                    alert('mem', err.WC_OBSERVER_SYS_MEM_TOO_LARGE.format(server=server, factor=factor), [suggest])

    global stdio, success
    success = True
    check_status = {}
    cluster_config = plugin_context.cluster_config
    INF = float('inf')
    plugin_context.set_variable('start_check_status', check_status)

    kernel_check_items = [
        {'check_item': 'vm.max_map_count', 'need': [327600, 1310720], 'recommend': 655360},
        {'check_item': 'vm.min_free_kbytes', 'need': [32768, 2097152], 'recommend': 2097152},
        {'check_item': 'vm.overcommit_memory', 'need': 0, 'recommend': 0},
        {'check_item': 'fs.file-max', 'need': [6573688, INF], 'recommend': 6573688},
    ]

    kernel_check_status = {}
    for kernel_param in kernel_check_items:
        check_item = kernel_param['check_item']
        kernel_check_status[check_item] = err.CheckStatus()

    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
            'mem': err.CheckStatus(),
            'disk': err.CheckStatus(),
            'dir': err.CheckStatus(),
            'ulimit': err.CheckStatus(),
            'aio': err.CheckStatus(),
            'net': err.CheckStatus(),
            'ntp': err.CheckStatus(),
            'ocp tenant memory': err.CheckStatus(),
            'ocp tenant disk': err.CheckStatus()
        }
        check_status[server].update(kernel_check_status)

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_clients = {}
    servers_port = {}
    servers_memory = {}
    servers_disk = {}
    servers_clog_mount = {}
    servers_net_interface = {}
    servers_dirs = {}
    servers_check_dirs = {}
    servers_log_disk_size = {}
    servers_min_pool_memory = {}
    PRO_MEMORY_MIN = 16 << 30
    PRO_POOL_MEM_MIN = 2147483648
    START_NEED_MEMORY = 3 << 30
    global_generate_config = plugin_context.get_variable('global_generate_config', default=generate_configs.get('global', {}))
    plugin_context.set_variable('global_generate_config', global_generate_config)
    stdio.start_loading('Check before {} observer'.format(source_option))

    need_bootstrap = True
    parameter_check = True
    port_check = True
    kernel_check = True
    is_running_opt = source_option in ['restart', 'upgrade']
    upgrade_opt = source_option == 'upgrade'
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_generate_config = generate_configs.get(server, {})
        servers_clients[ip] = client
        server_config = cluster_config.get_server_conf_with_default(server)
        original_server_conf = cluster_config.get_original_server_conf_with_global(server)
        home_path = server_config['home_path']
        production_mode = server_config.get('production_mode', False)
        if not precheck:
            if need_bootstrap:
                data_dir = server_config['data_dir'] if server_config.get('data_dir') else '%s/store' % home_path
                if client.execute_command('ls %s/clog/tenant_1/' % data_dir).stdout.strip():
                    need_bootstrap = False
            remote_pid_path = '%s/run/observer.pid' % home_path
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is runnning, skip' % server)
                    work_dir_check = False
                    for repository in plugin_context.repositories:
                        if repository.name == cluster_config.name:
                            break
                    port_check = upgrade_opt and not has_obshell(repository)
                    parameter_check = False
                    kernel_check = is_running_opt

        if work_dir_check:
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]

            if not server_config.get('data_dir'):
                server_config['data_dir'] = '%s/store' % home_path
            if not server_config.get('redo_dir'):
                server_config['redo_dir'] = server_config['data_dir']
            if not server_config.get('clog_dir'):
                server_config['clog_dir'] = '%s/clog' % server_config['redo_dir']
            if not server_config.get('ilog_dir'):
                server_config['ilog_dir'] = '%s/ilog' % server_config['redo_dir']
            if not server_config.get('slog_dir'):
                server_config['slog_dir'] = '%s/slog' % server_config['data_dir']
            if server_config['redo_dir'] == server_config['data_dir']:
                keys = ['home_path', 'data_dir', 'clog_dir', 'ilog_dir', 'slog_dir']
            else:
                keys = ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']

            for key in keys:
                path = server_config.get(key)
                suggests = [err.SUG_CONFIG_CONFLICT_DIR.format(key=key, server=server)]
                if path in dirs and dirs[path]:
                    critical('dir', err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']), suggests)
                dirs[path] = {
                    'server': server,
                    'key': key,
                }
                if key not in original_server_conf:
                    continue
                empty_check = work_dir_empty_check
                while True:
                    if path in check_dirs:
                        if check_dirs[path] != True:
                            critical('dir', check_dirs[path], suggests)
                        break

                    if client.execute_command('bash -c "[ -a %s ]"' % path):
                        is_dir = client.execute_command('[ -d {} ]'.format(path))
                        has_write_permission = client.execute_command('[ -w {} ]'.format(path))
                        if is_dir and has_write_permission:
                            if empty_check:
                                ret = client.execute_command('ls %s' % path)
                                if not ret or ret.stdout.strip():
                                    check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(path=path))
                                else:
                                    check_dirs[path] = True
                            else:
                                check_dirs[path] = True
                        else:
                            if not is_dir:
                                check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.NOT_DIR.format(path=path))
                            else:
                                check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key, msg=err.InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=path))
                    else:
                        path = os.path.dirname(path)
                        empty_check = False

        if ip not in servers_port:
            servers_disk[ip] = {}
            servers_port[ip] = {}
            servers_clog_mount[ip] = {}
            servers_net_interface[ip] = {}
            servers_memory[ip] = {'num': 0, 'percentage': 0, 'servers': {}}
        memory = servers_memory[ip]
        ports = servers_port[ip]
        disk = servers_disk[ip]
        clog_mount = servers_clog_mount[ip]
        interfaces = servers_net_interface[ip]

        if port_check:
            stdio.verbose('%s port check' % server)
            if upgrade_opt:
                keys = ['obshell_port']
            else:
                keys = ['mysql_port', 'rpc_port', 'obshell_port']
            
            for key in keys:
                port = int(server_config.get(key))
                if port in ports:
                    critical(
                        'port',
                        err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                        [err.SUG_PORT_CONFLICTS.format()]
                    )
                    continue
                ports[port] = {
                    'server': server,
                    'key': key
                }
                if get_port_socket_inode(client, port):
                    critical('port', err.EC_CONFLICT_PORT.format(server=ip, port=port), [err.SUG_USE_OTHER_PORT.format()])

        if parameter_check:
            servers_min_pool_memory[server] = __min_full_resource_pool_memory = server_config.get('__min_full_resource_pool_memory')
            if production_mode and __min_full_resource_pool_memory < PRO_POOL_MEM_MIN:
                error('mem', err.EC_OBSERVER_PRODUCTION_MODE_LIMIT.format(server=server, key="__min_full_resource_pool_memory", limit=PRO_POOL_MEM_MIN), [err.SUB_SET_NO_PRODUCTION_MODE.format()])

            memory_limit = 0
            percentage = 0
            if server_config.get('memory_limit'):
                memory_limit = Capacity(server_config['memory_limit']).bytes
                if production_mode and memory_limit < PRO_MEMORY_MIN:
                    error('mem', err.EC_OBSERVER_PRODUCTION_MODE_LIMIT.format(server=server, key='memory_limit', limit=Capacity(PRO_MEMORY_MIN)), [err.SUB_SET_NO_PRODUCTION_MODE.format()])
                memory['num'] += memory_limit
            elif 'memory_limit_percentage' in server_config:
                percentage = server_config['memory_limit_percentage']
                memory['percentage'] += percentage
            else:
                percentage = 80
                memory['percentage'] += percentage
            memory['servers'][server] = {
                'num': memory_limit,
                'percentage': percentage,
                'system_memory': Capacity(server_config.get('system_memory', 0)).bytes
            }

            data_path = server_config['data_dir'] if server_config.get('data_dir') else  os.path.join(server_config['home_path'], 'store')
            redo_dir = server_config['redo_dir'] if server_config.get('redo_dir') else  data_path
            clog_dir = server_config['clog_dir'] if server_config.get('clog_dir') else  os.path.join(redo_dir, 'clog')
            if not client.execute_command('ls %s/sstable/block_file' % data_path):
                disk[data_path] = {'server': server}
                clog_mount[clog_dir] = {'server': server}
                if 'datafile_size' in server_config and server_config['datafile_size'] and server_config['datafile_size']:
                    # if need is string, it means use datafile_size
                    disk[data_path]['need'] = server_config['datafile_size']
                elif 'datafile_disk_percentage' in server_config and server_config['datafile_disk_percentage']:
                    # if need is integer, it means use datafile_disk_percentage
                    disk[data_path]['need'] = int(server_config['datafile_disk_percentage'])

                if 'log_disk_size' in server_config and server_config['log_disk_size'] and server_config['log_disk_size']:
                    # if need is string, it means use log_disk_size
                    clog_mount[clog_dir]['need'] = server_config['log_disk_size']
                elif 'log_disk_percentage' in server_config and server_config['log_disk_percentage']:
                    # if need is integer, it means use log_disk_percentage
                    clog_mount[clog_dir]['need'] = int(server_config['log_disk_percentage'])

                devname = server_config.get('devname')
                if devname:
                    if not client.execute_command("grep -e '^ *%s:' /proc/net/dev" % devname):
                        suggest = err.SUG_NO_SUCH_NET_DEVIC.format(ip=ip)
                        suggest.auto_fix = 'devname' not in global_generate_config and 'devname' not in server_generate_config
                        critical('net', err.EC_NO_SUCH_NET_DEVICE.format(server=server, devname=devname), suggests=[suggest])
                if devname not in interfaces:
                    interfaces[devname] = []
                interfaces[devname].append(ip)

    ip_server_memory_info = {}
    for ip in servers_disk:
        ip_servers = servers_memory[ip]['servers'].keys()
        server_num = len(ip_servers)
        client = servers_clients[ip]
        ret = client.execute_command('cat /proc/sys/fs/aio-max-nr /proc/sys/fs/aio-nr')
        if not ret:
            for server in ip_servers:
                alert('aio', err.EC_FAILED_TO_GET_AIO_NR.format(ip=ip), [err.SUG_CONNECT_EXCEPT.format()])
        else:
            try:
                max_nr, nr = ret.stdout.strip().split('\n')
                max_nr, nr = int(max_nr), int(nr)
                need = server_num * 20000
                RECD_AIO = 1048576
                if need > max_nr - nr:
                    for server in ip_servers:
                        critical('aio', err.EC_AIO_NOT_ENOUGH.format(ip=ip, avail=max_nr - nr, need=need), [err.SUG_SYSCTL.format(var='fs.aio-max-nr', value=max(RECD_AIO, need), ip=ip)])
                elif int(max_nr) < RECD_AIO:
                    for server in ip_servers:
                        alert('aio', err.WC_AIO_NOT_ENOUGH.format(ip=ip, current=max_nr), [err.SUG_SYSCTL.format(var='fs.aio-max-nr', value=RECD_AIO, ip=ip)])
            except:
                for server in ip_servers:
                    alert('aio', err.EC_FAILED_TO_GET_AIO_NR.format(ip=ip), [err.SUG_UNSUPPORT_OS.format()])
                stdio.exception('')

        ret = client.execute_command('ulimit -a')
        ulimits_min = {
            'open files': {
                'need': lambda x: 20000 * x,
                'recd': lambda x: 655350,
                'name': 'nofile'
            },
            'max user processes': {
                'need': lambda x: 120000,
                'recd': lambda x: 655350,
                'name': 'nproc'
            },
            'core file size': {
                'need': lambda x: 0,
                'recd': lambda x: INF,
                'below_need_error': False,
                'below_recd_error_strict': False,
                'name': 'core'
            },
            'stack size': {
                'need': lambda x: 1024,
                'recd': lambda x: INF,
                'below_recd_error_strict': False,
                'name': 'stack'
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
                for server in ip_servers:
                    alert('ulimit', '(%s) failed to get %s' % (ip, key), suggests=[err.SUG_UNSUPPORT_OS.format()])
            else:
                value = int(value)
                need = ulimits_min[key]['need'](server_num)
                if need > value:
                    if (strict_check or production_mode) and ulimits_min[key].get('below_recd_error_strict', True) and value < ulimits_min[key]['recd'](server_num):
                        need = ulimits_min[key]['recd'](server_num)
                    need = need if need != INF else 'unlimited'
                    for server in ip_servers:
                        if ulimits_min[key].get('below_need_error', True):
                            critical('ulimit', err.EC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value), [err.SUG_ULIMIT.format(name=ulimits_min[key]['name'], value=need, ip=ip)])
                        else:
                            alert('ulimit', err.EC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value), suggests=[err.SUG_ULIMIT.format(name=ulimits_min[key]['name'], value=need, ip=ip)])
                else:
                    need = ulimits_min[key]['recd'](server_num)
                    if need > value:
                        need = need if need != INF else 'unlimited'
                        for server in ip_servers:
                            if ulimits_min[key].get('below_recd_error_strict', True):
                                alert('ulimit', err.WC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value), suggests=[err.SUG_ULIMIT.format(name=ulimits_min[key]['name'], value=need, ip=ip)])
                            else:
                                stdio.warn(err.WC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value))

        if kernel_check:
            # check kernel params
            try:
                cmd = 'sysctl -a'
                ret = client.execute_command(cmd)
                if not ret:
                    alert_strict('kernel', err.EC_FAILED_TO_GET_PARAM.format(key='kernel parameter ', cmd=cmd), [err.SUG_CONNECT_EXCEPT.format(ip=ip)])
                    continue
                kernel_params = {}
                kernel_param_src = ret.stdout.split('\n')
                for kernel in kernel_param_src:
                    if not kernel:
                        continue
                    kernel = kernel.split('=')
                    kernel_params[kernel[0].strip()] = re.findall(r"[-+]?\d+", kernel[1])

                for kernel_param in kernel_check_items:
                    check_item = kernel_param['check_item']
                    if check_item not in kernel_params:
                        continue
                    values = kernel_params[check_item]
                    needs = kernel_param['need']
                    recommends = kernel_param['recommend']
                    for i in range(len(values)):
                        # This case is not handling the value of 'default'. Additional handling is required for 'default' in the future.
                        item_value = int(values[i])
                        need = needs[i] if isinstance(needs, tuple) else needs
                        recommend = recommends[i] if isinstance(recommends, tuple) else recommends
                        if isinstance(need, list):
                            if item_value < need[0] or item_value > need[1]:
                                suggest = [err.SUG_SYSCTL.format(var=check_item, value=' '.join(str(i) for i in recommend) if isinstance(recommend, list) else recommend, ip=ip)]
                                need = 'within {}'.format(needs) if needs[-1] != INF else 'greater than {}'.format(needs[0])
                                now = '[{}]'.format(', '.join(values)) if len(values) > 1 else item_value
                                alert_strict(check_item, err.EC_PARAM_NOT_IN_NEED.format(ip=ip, check_item=check_item, need=need, now=now, recommend=recommends), suggest)
                                break
                        elif item_value != need:
                            alert_strict(check_item, err.EC_PARAM_NOT_IN_NEED.format(ip=ip, check_item=check_item, need=needs, recommend=recommend, now=item_value), [err.SUG_SYSCTL.format(var=check_item, value=recommend, ip=ip)])
            except:
                stdio.exception('')

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
                    error('mem', err.EC_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE.format(ip=ip, available=Capacity(server_memory_stats['available']), need=Capacity(min_start_need)), [err.SUG_OBSERVER_NOT_ENOUGH_MEMORY_ALAILABLE.format(ip=ip)])
            elif total_use > server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached']:
                for server in ip_servers:
                    server_generate_config = generate_configs.get(server, {})
                    suggest = err.SUG_OBSERVER_REDUCE_MEM.format()
                    suggest.auto_fix = True
                    for key in ['memory_limit', 'memory_limit_percentage']:
                        if key in global_generate_config or key in server_generate_config:
                            suggest.auto_fix = False
                            break
                    error('mem', err.EC_OBSERVER_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=Capacity(server_memory_stats['free']), cached=Capacity(server_memory_stats['buffers'] + server_memory_stats['cached']), need=Capacity(total_use)), [suggest])
            elif total_use > server_memory_stats['free']:
                system_memory_check()
                for server in ip_servers:
                    alert('mem', err.EC_OBSERVER_NOT_ENOUGH_MEMORY.format(ip=ip, free=Capacity(server_memory_stats['free']), need=Capacity(total_use)), [err.SUG_OBSERVER_REDUCE_MEM.format()])
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
            slog_size = float(4 << 30)
            if isinstance(need, int):
                # slog need 4G
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
                    alert('disk', err.WC_OBSERVER_SAME_DISK.format(ip=ip, disk=p), suggests)
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
                    critical('disk', err.EC_OBSERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=p, avail=Capacity(avail), need=Capacity(need)), tmp_suggests + suggests)

    global_conf = cluster_config.get_global_conf()
    has_ocp = 'ocp-express' in plugin_context.components or 'ocp-server-ce' in plugin_context.components
    if not has_ocp and any([key.startswith('ocp_meta') for key in global_conf]):
        has_ocp = True

    if has_ocp and need_bootstrap and parameter_check:
        global_conf_with_default = copy.deepcopy(cluster_config.get_global_conf_with_default())
        original_global_conf = cluster_config.get_original_global_conf()
        tenants_componets_map = {
            "meta": ["ocp-express", "ocp-server", "ocp-server-ce"],
            "monitor": ["ocp-server", "ocp-server-ce"],
        }
        tenant_memory = tenant_log_disk = memory_limit = system_memory = log_disk_size = sys_log_disk_size = 0
        for tenant, component_list in tenants_componets_map.items():
            prefix = "ocp_%s_tenant_" % tenant
            tenant_key = "ocp_%s_tenant" % tenant
            for key in global_conf_with_default:
                if key.startswith(prefix) and not original_global_conf.get(key, None):
                    global_conf_with_default['ocp_%s_tenant' % tenant][key.replace(prefix, '', 1)] = global_conf_with_default[key]
            if set(list(plugin_context.components)) & set(component_list):
                tenant_memory_default = global_conf_with_default[tenant_key].get('memory_size', '0')
                tenant_memory += Capacity(original_global_conf.get(tenant_key, {}).get('memory_size', tenant_memory_default)).bytes
                tenant_log_disk_default = global_conf_with_default[tenant_key].get('log_disk_size', '0')
                tenant_log_disk += Capacity(original_global_conf.get(tenant_key, {}).get('log_disk_size', tenant_log_disk_default)).bytes

        servers_sys_memory = {}
        if tenant_memory:
            sys_memory_size = None
            if 'sys_tenant' in global_conf and 'memory_size' in global_conf['sys_tenant']:
                sys_memory_size = global_conf['sys_tenant']['memory_size']
            for server in cluster_config.servers:
                if server.ip not in servers_memory or server not in servers_memory[server.ip]['servers'] or server not in servers_min_pool_memory:
                    stdio.verbose('skip server {} for missing some memory info.'.format(server))
                    continue
                memory_limit = servers_memory[server.ip]['servers'][server]['num']
                system_memory = servers_memory[server.ip]['servers'][server]['system_memory']
                min_pool_memory = servers_min_pool_memory[server]
                if system_memory == 0:
                    system_memory = get_system_memory(memory_limit)
                if not sys_memory_size:
                    sys_memory_size = servers_sys_memory[server] = max(min_pool_memory, min((memory_limit - system_memory) * 0.25, Capacity('16G').bytes))
                if tenant_memory + system_memory + sys_memory_size <= memory_limit:
                    break
            else:
                ocp_meta_tenant_mem = original_global_conf.get('ocp_meta_tenant', {}).get('memory_size', global_conf_with_default['ocp_meta_tenant'].get('memory_size', '0'))
                ocp_monitor_tenant_mem = original_global_conf.get('ocp_monitor_tenant', {}).get('memory_size', global_conf_with_default['ocp_monitor_tenant'].get('memory_size', '0'))
                critical('ocp tenant memory', err.EC_OCP_SERVER_NOT_EXIST_METADB_TENANT_MEMORY_NOT_ENOUGH.format(avail=Capacity(memory_limit - system_memory - sys_memory_size), need=Capacity(tenant_memory), memory_limit=Capacity(memory_limit), system_memory=Capacity(system_memory), sys_tenant_memory=Capacity(sys_memory_size), ocp_meta_tenant_memory=Capacity(ocp_meta_tenant_mem), ocp_monitor_tenant_memory=Capacity(ocp_monitor_tenant_mem)), [err.SUG_OCP_SERVER_NOT_EXIST_METADB_TENANT_NOT_ENOUGH.format()])

        if tenant_log_disk:
            for server in cluster_config.servers:
                log_disk_size = servers_log_disk_size[server]
                sys_log_disk_size = servers_sys_memory.get(server, 0)
                if tenant_log_disk + sys_log_disk_size <= log_disk_size:
                    break
            else:
                critical('ocp tenant disk', err.EC_OCP_SERVER_RESOURCE_NOT_ENOUGH.format(resource='log_disk_size', avail=Capacity(log_disk_size - sys_log_disk_size), need=Capacity(tenant_log_disk)))

    if success:
        for ip in servers_net_interface:
            client = servers_clients[ip]
            is_check_ping_permission = False
            for devname in servers_net_interface[ip]:
                if not is_check_ping_permission:
                    ret = client.execute_command('ping -W 1 -c 1 127.0.0.1')
                    if ret.code == 127:
                        critical('net', err.EC_OBSERVER_PING_NOT_FOUND.format())
                        break
                    if not ret:
                        critical('net', err.EC_OBSERVER_PING_FAILED_SUID.format())
                        break
                    is_check_ping_permission = True
                if client.is_localhost() and (devname != 'lo' and devname is not None) or (not client.is_localhost() and devname == 'lo'):
                    suggest = err.SUG_NO_SUCH_NET_DEVIC.format(ip=ip)
                    suggest.auto_fix = client.is_localhost() and 'devname' not in global_generate_config and 'devname' not in server_generate_config
                    for server in ip_servers:
                        critical('net', err.EC_OBSERVER_PING_FAILED.format(ip1=ip, devname=devname, ip2=ip), [suggest])
                    continue
                for _ip in servers_clients:
                    if ip == _ip:
                        continue
                    ping_cmd = 'ping -W 1 -c 1 -I %s %s' % (devname, _ip) if devname is not None else 'ping -W 1 -c 1 %s' % _ip
                    if not client.execute_command(ping_cmd):
                        suggest = err.SUG_NO_SUCH_NET_DEVIC.format(ip=ip)
                        suggest.auto_fix = 'devname' not in global_generate_config and 'devname' not in server_generate_config
                        for server in ip_servers:
                            if devname is not None:
                                critical('net', err.EC_OBSERVER_PING_FAILED.format(ip1=ip, devname=devname, ip2=_ip), [suggest])
                            else:
                                critical('net', err.EC_OBSERVER_PING_FAILED_WITH_NO_DEVNAME.format(ip1=ip, ip2=_ip), [suggest])
                        break


    if success:
        times = []
        for ip in servers_clients:
            client = servers_clients[ip]
            delta = time_delta(client)
            stdio.verbose('%s time delta %s' % (ip, delta))
            times.append(delta)
        if times and max(times) - min(times) > 500:
            critical('ntp', err.EC_OBSERVER_TIME_OUT_OF_SYNC.format(), [err.SUG_OBSERVER_TIME_OUT_OF_SYNC.format()])
    for server in cluster_config.servers:
        status = check_status[server]
        for key in status:
            if status[key].status == err.CheckStatus.WAIT:
                status[key].status = err.CheckStatus.PASS

    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')


