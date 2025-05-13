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

import os
import re

import _errno as err
from tool import get_port_socket_inode


def environment_check(plugin_context, work_dir_empty_check=True, generate_configs={}, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    servers_clients = plugin_context.get_variable('servers_clients')
    critical = plugin_context.get_variable('critical')
    servers_port = plugin_context.get_variable('servers_port')
    servers_net_interface = plugin_context.get_variable('servers_net_interface')
    work_dir_check = plugin_context.get_variable('work_dir_check')
    port_check = plugin_context.get_variable('port_check')
    servers_memory = plugin_context.get_variable('servers_memory')
    slog_dir_key = plugin_context.get_variable('slog_dir_key')
    check_item_status_pass = plugin_context.get_variable('check_item_status_pass')
    success = plugin_context.get_variable('get_success')()

    servers_dirs = {}
    servers_check_dirs = {}
    global_generate_config = generate_configs.get('global', {})

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        servers_clients[ip] = client
        server_generate_config = generate_configs.get(server, {})
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']

        if work_dir_check:
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            original_server_conf = cluster_config.get_server_conf(server)

            if not server_config.get('data_dir'):
                server_config['data_dir'] = '%s/store' % home_path
            if not server_config.get('redo_dir'):
                server_config['redo_dir'] = server_config['data_dir']
            if not server_config.get('clog_dir'):
                server_config['clog_dir'] = '%s/clog' % server_config['redo_dir']
            if not server_config.get('ilog_dir'):
                server_config['ilog_dir'] = '%s/ilog' % server_config['redo_dir']
            if not server_config.get('slog_dir'):
                server_config['slog_dir'] = '%s/slog' % server_config[slog_dir_key]
            if server_config['redo_dir'] == server_config['data_dir']:
                keys = ['home_path', 'data_dir', 'clog_dir', 'ilog_dir', 'slog_dir']
            else:
                keys = ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']

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

        ports = servers_port[ip]

        if port_check:
            stdio.verbose('%s port check' % server)
            for key in ['mysql_port', 'rpc_port']:
                port = int(server_config[key])
                if port in ports:
                    critical(server, 
                        'port',
                        err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                        [err.SUG_PORT_CONFLICTS.format()]
                    )
                    continue
                ports[port] = {
                    'server': server,
                    'key': key
                }
                if get_port_socket_inode(client, port, stdio):
                    critical(server, 
                        'port',
                        err.EC_CONFLICT_PORT.format(server=ip, port=port),
                        [err.SUG_USE_OTHER_PORT.format()]
                    )

        if len(re.findall(r'(^avx\s+)|(\s+avx\s+)|(\s+avx$)', client.execute_command('lscpu | grep avx').stdout)) == 0 and os.uname()[4].startswith('x86'):
            critical(server, 'cpu', err.EC_CPU_NOT_SUPPORT_AVX.format(server=server), [err.SUG_CHANGE_SERVER.format()])
    if success:
        for ip in servers_net_interface:
            client = servers_clients[ip]
            ip_servers = servers_memory[ip]['servers'].keys()
            if servers_net_interface[ip].get(None):
                devinfo = client.execute_command('cat /proc/net/dev').stdout
                interfaces = []
                for interface in re.findall('\n\s+(\w+):', devinfo):
                    if interface != 'lo':
                        interfaces.append(interface)
                if not interfaces:
                    interfaces = ['lo']
                if len(interfaces) > 1:
                    servers = ','.join(str(server) for server in servers_net_interface[ip][None])
                    suggest = err.SUG_NO_SUCH_NET_DEVIC.format(ip=ip)
                    for server in ip_servers:
                        critical(server, 'net', err.EC_OBSERVER_MULTI_NET_DEVICE.format(ip=ip, server=servers), [suggest])
                else:
                    servers_net_interface[ip][interfaces[0]] = servers_net_interface[ip][None]
                    del servers_net_interface[ip][None]
    if success:
        for ip in servers_net_interface:
            client = servers_clients[ip]
            is_check_ping_permission = False
            for devname in servers_net_interface[ip]:
                if not is_check_ping_permission:
                    for server in cluster_config.servers:
                        if server.ip == ip:
                            break
                    ret = client.execute_command('ping -W 1 -c 1 127.0.0.1')
                    if ret.code == 127:
                        critical(server, 'net', err.EC_OBSERVER_PING_NOT_FOUND.format())
                        break
                    if not ret:
                        critical(server, 'net', err.EC_OBSERVER_PING_FAILED_SUID.format())
                        break
                    is_check_ping_permission = True
                if client.is_localhost() and (devname != 'lo' and devname is not None) or (not client.is_localhost() and devname == 'lo'):
                    suggest = err.SUG_NO_SUCH_NET_DEVIC.format(ip=ip)
                    suggest.auto_fix = client.is_localhost() and 'devname' not in global_generate_config and 'devname' not in server_generate_config
                    for server in ip_servers:
                        critical(server, 'net', err.EC_OBSERVER_PING_FAILED.format(ip1=ip, devname=devname, ip2=ip), [suggest])
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
                                critical(server, 'net', err.EC_OBSERVER_PING_FAILED.format(ip1=ip, devname=devname, ip2=_ip), [suggest])
                            else:
                                critical(server, 'net', err.EC_OBSERVER_PING_FAILED_WITH_NO_DEVNAME.format(ip1=ip, ip2=_ip), [suggest])
                        break
    plugin_context.set_variable('servers_net_interface', servers_net_interface)
    plugin_context.set_variable('servers_port', servers_port)

    if not success:
        system_env_error = False
        kernel_check_items = plugin_context.get_variable('kernel_check_items')
        for check_item in kernel_check_items:
            if check_item_status_pass(check_item['check_item']):
                system_env_error = True
                break
        else:
            if not check_item_status_pass('aio') or not check_item_status_pass('ulimit'):
                system_env_error = True
        return plugin_context.return_false(system_env_error=system_env_error)
    return plugin_context.return_true()

