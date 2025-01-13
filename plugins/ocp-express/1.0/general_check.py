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

from _rpm import Version
import _errno as err
from _types import Capacity
from tool import get_port_socket_inode


def get_mount_path(disk, _path):
    _mount_path = '/'
    for p in disk:
        if p in _path:
            if len(p) > len(_mount_path):
                _mount_path = p
    return _mount_path


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


def general_check(plugin_context, work_dir_check=False, work_dir_empty_check=True, precheck=False, java_check=True, *args, **kwargs):

    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    alert = plugin_context.get_variable('alert')
    error = plugin_context.get_variable('error')
    get_missing_required_parameters = plugin_context.get_variable('get_missing_required_parameters')
    env = plugin_context.get_variable('start_env')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    stdio.start_loading('Check before start ocp-express')
    if not env:
        return plugin_context.return_false()

    server_port = {}
    servers_dirs = {}
    servers_check_dirs = {}
    for server in cluster_config.servers:
        client = clients[server]
        server_config = env[server]
        missed_keys = get_missing_required_parameters(server_config)
        if missed_keys:
            stdio.error(err.EC_NEED_CONFIG.format(server=server, component=cluster_config.name, miss_keys=missed_keys))
            continue
        home_path = server_config['home_path']
        if not precheck:
            remote_pid_path = '%s/run/ocp-express.pid' % home_path
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is running, skip' % server)
                    wait_2_pass(server)
                    continue

        if work_dir_check:
            ip = server.ip
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            original_server_conf = cluster_config.get_server_conf(server)

            keys = ['home_path', 'log_dir']
            for key in keys:
                path = server_config.get(key)
                suggests = [err.SUG_CONFIG_CONFLICT_DIR.format(key=key, server=server)]
                if path in dirs and dirs[path]:
                    critical(server, 'dir', err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']), suggests)
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
                            critical(server, 'dir', check_dirs[path], suggests)
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

        port = server_config['port']
        ip = server.ip
        if ip not in server_port:
            server_port[ip] = {}
        ports = server_port[ip]
        if port in server_port[ip]:
            critical(
                server,
                'port',
                err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'],
                                                   key=ports[port]['key']),
                [err.SUG_PORT_CONFLICTS.format()]
            )
            continue
        ports[port] = {
            'server': server,
            'key': 'port'
        }
        if get_port_socket_inode(client, port):
            critical(
                server,
                'port',
                err.EC_CONFLICT_PORT.format(server=ip, port=port),
                [err.SUG_USE_OTHER_PORT.format()]
            )
            continue
        check_pass(server, 'port')

    # java version check
    if java_check:
        for server in cluster_config.servers:
            client = clients[server]
            server_config = env[server]
            java_bin = server_config['java_bin']
            client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
            ret = client.execute_command('{} -version'.format(java_bin))
            if not ret:
                critical(server, 'java', err.EC_OCP_EXPRESS_JAVA_NOT_FOUND.format(server=server), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0')])
                continue
            version_pattern = r'version\s+\"(\d+\.\d+.\d+)'
            found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
            if not found:
                error(server, 'java', err.EC_OCP_EXPRESS_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
                continue
            java_major_version = found.group(1)
            if Version(java_major_version) != Version('1.8.0'):
                critical(server, 'java', err.EC_OCP_EXPRESS_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_EXPRESS_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
                continue

    servers_memory = {}
    servers_disk = {}
    servers_client = {}
    ip_servers = {}

    for server in cluster_config.servers:
        client = clients[server]
        server_config = env[server]
        memory_size = Capacity(server_config['memory_size']).bytes
        if server_config.get('log_dir'):
            log_dir = server_config['log_dir']
        else:
            log_dir = os.path.join(server_config['home_path'], 'log')
        need_size = Capacity(server_config['logging_file_total_size_cap']).bytes
        ip = server.ip
        if ip not in servers_client:
            servers_client[ip] = client
        if ip not in servers_memory:
            servers_memory[ip] = {
                'need': memory_size,
                'server_num': 1
            }
        else:
            servers_memory[ip]['need'] += memory_size
            servers_memory[ip]['server_num'] += 1
        if ip not in servers_disk:
            servers_disk[ip] = {}
        if log_dir not in servers_disk[ip]:
            servers_disk[ip][log_dir] = need_size
        else:
            servers_disk[ip][log_dir] += need_size
        if ip not in ip_servers:
            ip_servers[ip] = [server]
        else:
            ip_servers[ip].append(server)
    # memory check
    for ip in servers_memory:
        client = servers_client[ip]
        memory_needed = servers_memory[ip]['need']
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
            mem_suggests = [err.SUG_OCP_EXPRESS_REDUCE_MEM.format()]
            if memory_needed * 0.5 > server_memory_stats['available']:
                for server in ip_servers[ip]:
                    error(server, 'mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY_AVAILABLE.format(ip=ip, available=Capacity(server_memory_stats['available']), need=Capacity(memory_needed)), suggests=mem_suggests)
            elif memory_needed > server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached']:
                for server in ip_servers[ip]:
                    error(server, 'mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=Capacity(server_memory_stats['free']), cached=Capacity(server_memory_stats['buffers'] + server_memory_stats['cached']), need=Capacity(memory_needed)), suggests=mem_suggests)
            elif memory_needed > server_memory_stats['free']:
                for server in ip_servers[ip]:
                    alert(server, 'mem', err.EC_OCP_EXPRESS_NOT_ENOUGH_MEMORY.format(ip=ip,  free=Capacity(server_memory_stats['free']), need=Capacity(memory_needed)), suggests=mem_suggests)
    # disk check
    for ip in servers_disk:
        client = servers_client[ip]
        disk_info = get_disk_info(all_paths=servers_disk[ip], client=client, stdio=stdio)
        if disk_info:
            for path in servers_disk[ip]:
                disk_needed = servers_disk[ip][path]
                mount_path = get_mount_path(disk_info, path)
                if disk_needed > disk_info[mount_path]['avail']:
                    for server in ip_servers[ip]:
                        error(server, 'disk', err.EC_OCP_EXPRESS_NOT_ENOUGH_DISK.format(ip=ip, disk=mount_path, need=Capacity(disk_needed), avail=Capacity(disk_info[mount_path]['avail'])), suggests=[err.SUG_OCP_EXPRESS_REDUCE_DISK.format()])
        else:
            stdio.warn(err.WC_OCP_EXPRESS_FAILED_TO_GET_DISK_INFO.format(ip))
    plugin_context.set_variable('start_env', env)

    for server in cluster_config.servers:
        wait_2_pass(server)

    success = plugin_context.get_variable('get_success')()
    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
