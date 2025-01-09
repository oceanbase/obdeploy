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
import datetime

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


def get_disk_info_by_path(ocp_user, path, client, stdio):
    disk_info = {}
    ret = client.execute_command(execute_cmd(ocp_user, 'df --block-size=1024 {}'.format(path)))
    if ret:
        for total, used, avail, puse, path in re.findall(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+%)\s+(.+)', ret.stdout):
            disk_info[path] = {'total': int(total) << 10, 'avail': int(avail) << 10, 'need': 0}
            stdio.verbose('get disk info for path {}, total: {} avail: {}'.format(path, disk_info[path]['total'], disk_info[path]['avail']))
    return disk_info


def get_disk_info(all_paths, client, ocp_user, stdio):
    overview_ret = True
    disk_info = get_disk_info_by_path(ocp_user, '', client, stdio)
    if not disk_info:
        overview_ret = False
        disk_info = get_disk_info_by_path(ocp_user, '/', client, stdio)
        if not disk_info:
            disk_info['/'] = {'total': 0, 'avail': 0, 'need': 0}
    all_path_success = {}
    for path in all_paths:
        all_path_success[path] = False
        cur_path = path
        while cur_path not in disk_info:
            disk_info_for_current_path = get_disk_info_by_path(ocp_user, cur_path, client, stdio)
            if disk_info_for_current_path:
                disk_info.update(disk_info_for_current_path)
                all_path_success[path] = True
                break
            else:
                cur_path = os.path.dirname(cur_path)
    if overview_ret or all(all_path_success.values()):
        return disk_info


def execute_cmd(ocp_user, cmd):
    return cmd if not ocp_user else 'sudo ' + cmd


def general_check(plugin_context, work_dir_check=False, work_dir_empty_check=True, precheck=False, source_option="start", *args, **kwargs):

    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    alert = plugin_context.get_variable('alert')
    error = plugin_context.get_variable('error')
    cursor = plugin_context.get_variable('cursor')
    get_missing_required_parameters = plugin_context.get_variable('get_missing_required_parameters')
    env = plugin_context.get_variable('start_env')

    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    stdio.start_loading('Check before start %s' % cluster_config.name)
    if not env:
        return plugin_context.return_false()

    stdio.verbose('oceanbase version check')
    versions_check = {
        "oceanbase version": {
            'comps': ['oceanbase', 'oceanbase-ce'],
            'min_version': Version('4.0')
        },
    }
    repo_versions = {}
    for repository in plugin_context.repositories:
        repo_versions[repository.name] = repository.version

    for check_item in versions_check:
        for comp in versions_check[check_item]['comps']:
            if comp not in cluster_config.depends:
                continue
            depend_comp_version = repo_versions.get(comp)
            if depend_comp_version is None:
                stdio.verbose('failed to get {} version, skip version check'.format(comp))
                continue
            min_version = versions_check[check_item]['min_version']
            if depend_comp_version < min_version:
                critical(servers[0], check_item, err.EC_OCP_SERVER_DEPENDS_COMP_VERSION.format(ocp_server_version=cluster_config.version, comp=comp, comp_version=min_version))

    server_port = {}
    servers_dirs = {}
    servers_check_dirs = {}
    for server in cluster_config.servers:
        client = clients[server]

        server_config = env[server]
        ocp_user = server_config.get('launch_user', '')
        missed_keys = get_missing_required_parameters(server_config)
        if missed_keys:
            error(server, err.EC_NEED_CONFIG.format(server=server, component=cluster_config.name, miss_keys=missed_keys))
        home_path = server_config['home_path']
        if not precheck:
            remote_pid_path = '%s/run/ocp-server.pid' % home_path
            remote_pid = client.execute_command(execute_cmd(ocp_user, 'cat %s' % remote_pid_path)).stdout.strip()
            if remote_pid:
                if client.execute_command(execute_cmd(ocp_user, 'ls /proc/%s' % remote_pid)):
                    stdio.verbose('%s is running, skip' % server)
                    wait_2_pass(server)
                    continue

        if not cluster_config.depends:
            # time check
            stdio.verbose('time check ')
            now = client.execute_command('date +"%Y-%m-%d %H:%M:%S"').stdout.strip()
            now = datetime.datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
            stdio.verbose('now: %s' % now)
            stdio.verbose('cursor: %s' % cursor)
            if cursor:
                ob_time = cursor.fetchone("SELECT NOW() now")['now']
                stdio.verbose('ob_time: %s' % ob_time)
                if not abs((now - ob_time).total_seconds()) < 180:
                    critical(server, 'time check', err.EC_OCP_SERVER_TIME_SHIFT.format(server=server))

        # user check
        stdio.verbose('user check ')
        if ocp_user:
            client = clients[server]
            if not client.execute_command(execute_cmd(ocp_user, "id -u %s" % ocp_user)):
                critical(server, 'launch user', err.EC_OCP_SERVER_LAUNCH_USER_NOT_EXIST.format(server=server, user=ocp_user))

        if work_dir_check:
            ip = server.ip
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            original_server_conf = cluster_config.get_server_conf(server)

            keys = ['home_path', 'log_dir', 'soft_dir']
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

                    if client.execute_command(execute_cmd(ocp_user, 'bash -c "[ -a %s ]"' % path)):
                        is_dir = client.execute_command(execute_cmd(ocp_user, '[ -d {} ]'.format(path)))
                        has_write_permission = client.execute_command(execute_cmd(ocp_user, '[ -w {} ]'.format(path)))
                        if is_dir and has_write_permission:
                            if empty_check:
                                check_privilege_cmd = "ls %s" % path
                                if server_config.get('launch_user', ''):
                                    check_privilege_cmd = "sudo su - %s -c 'ls %s'" % (server_config['launch_user'], path)
                                ret = client.execute_command(check_privilege_cmd)
                                if not ret:
                                    check_dirs[path] = err.EC_OCP_SERVER_DIR_ACCESS_FORBIDE.format(server=server, path=path, cur_path=path)
                                elif ret.stdout.strip():
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
        stdio.verbose('port check ')
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
        ports[port] = {
            'server': server,
            'key': 'port'
        }
        if source_option == 'start' and get_port_socket_inode(client, port):
            critical(
                server,
                'port',
                err.EC_CONFLICT_PORT.format(server=ip, port=port),
                [err.SUG_USE_OTHER_PORT.format()]
            )
        check_pass(server, 'port')

        servers_memory = {}
        servers_disk = {}
        servers_client = {}
        ip_servers = {}
        MIN_MEMORY_VALUE = 1073741824

        memory_size = Capacity(server_config.get('memory_size', '1G')).bytes
        if server_config.get('log_dir'):
            log_dir = server_config['log_dir']
        else:
            log_dir = os.path.join(server_config['home_path'], 'log')
        need_size = Capacity(server_config.get('logging_file_total_size_cap', '1G')).bytes
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
        stdio.verbose('memory check ')
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
                mem_suggests = [err.SUG_OCP_SERVER_REDUCE_MEM.format()]
                if memory_needed > server_memory_stats['available']:
                    for server in ip_servers[ip]:
                        error(server, 'mem', err.EC_OCP_SERVER_NOT_ENOUGH_MEMORY_AVAILABLE.format(ip=ip, available=str(Capacity(server_memory_stats['available'])), need=str(Capacity(memory_needed))), suggests=mem_suggests)
                elif memory_needed > server_memory_stats['free'] + server_memory_stats['buffers'] + server_memory_stats['cached']:
                    for server in ip_servers[ip]:
                        error(server, 'mem', err.EC_OCP_SERVER_NOT_ENOUGH_MEMORY_CACHED.format(ip=ip, free=str(Capacity(server_memory_stats['free'])), cached=str(Capacity(server_memory_stats['buffers'] + server_memory_stats['cached'])), need=str(Capacity(memory_needed))), suggests=mem_suggests)
                elif server_memory_stats['free'] < MIN_MEMORY_VALUE:
                    for server in ip_servers[ip]:
                        alert(server, 'mem', err.EC_OCP_SERVER_NOT_ENOUGH_MEMORY.format(ip=ip,  free=str(Capacity(server_memory_stats['free'])), need=str(Capacity(memory_needed))), suggests=mem_suggests)
        # disk check
        stdio.verbose('disk check ')
        for ip in servers_disk:
            client = servers_client[ip]
            disk_info = get_disk_info(all_paths=servers_disk[ip], client=client, ocp_user=ocp_user, stdio=stdio)
            if disk_info:
                for path in servers_disk[ip]:
                    disk_needed = servers_disk[ip][path]
                    mount_path = get_mount_path(disk_info, path)
                    if disk_needed > disk_info[mount_path]['avail']:
                        for server in ip_servers[ip]:
                            error(server, 'disk', err.EC_OCP_SERVER_NOT_ENOUGH_DISK.format(ip=ip, disk=mount_path, need=str(Capacity(disk_needed)), avail=str(Capacity(disk_info[mount_path]['avail']))), suggests=[err.SUG_OCP_SERVER_REDUCE_DISK.format()])
            else:
                stdio.warn(err.WC_OCP_SERVER_FAILED_TO_GET_DISK_INFO.format(ip))

        plugin_context.set_variable('start_env', env)

    for server in cluster_config.servers:
        wait_2_pass(server)

    success = plugin_context.get_variable('get_success')()
    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
