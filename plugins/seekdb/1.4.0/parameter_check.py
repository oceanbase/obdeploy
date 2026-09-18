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
import platform

import _errno as err
from _types import Capacity
from const import PLATFORM_DARWIN
from seekdb_14_parameters import get_unsupported_parameters

IS_DARWIN = platform.system() == PLATFORM_DARWIN

def parameter_check(plugin_context, generate_configs={}, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients

    servers_clients = plugin_context.get_variable('servers_clients')
    check_pass = plugin_context.get_variable('check_pass')
    check_fail = plugin_context.get_variable('check_fail')
    wait_2_pass = plugin_context.get_variable('wait_2_pass')
    alert = plugin_context.get_variable('alert')
    alert_strict = plugin_context.get_variable('alert_strict')
    error = plugin_context.get_variable('error')
    critical = plugin_context.get_variable('critical')
    print_with_suggests = plugin_context.get_variable('print_with_suggests')
    servers_memory = plugin_context.get_variable('servers_memory')
    servers_disk = plugin_context.get_variable('servers_disk')
    servers_clog_mount = plugin_context.get_variable('servers_clog_mount')
    servers_net_interface = plugin_context.get_variable('servers_net_interface')
    parameter_check = plugin_context.get_variable('parameter_check')

    global_generate_config = generate_configs.get('global', {})
    servers_min_pool_memory = {}
    PRO_POOL_MEM_MIN = 1073741824 if cluster_config.name == 'oceanbase-standalone' else 2147483648
    PRO_MEMORY_MIN = 16 << 30

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_generate_config = generate_configs.get(server, {})
        servers_clients[ip] = client
        server_config = cluster_config.get_server_conf_with_default(server)
        user_server_config = cluster_config.get_explicit_server_conf(server, format_conf=True)

        memory = servers_memory[ip]
        disk = servers_disk[ip]
        clog_mount = servers_clog_mount[ip]
        interfaces = servers_net_interface[ip]
        production_mode = server_config.get('production_mode', False)

        legacy_memory_keys, removed_keys = get_unsupported_parameters(user_server_config)
        if legacy_memory_keys:
            error(
                server,
                'mem',
                'SeekDB 1.4 does not support OBD memory settings %s. Use `memory_budget` instead.'
                % ', '.join(legacy_memory_keys),
            )
        if removed_keys:
            error(
                server,
                'parameter',
                'SeekDB 1.4 removed server parameters %s. Remove or migrate these settings before deployment.'
                % ', '.join(removed_keys),
            )

        if parameter_check:
            servers_min_pool_memory[server] = 0
            memory_limit = 0
            percentage = 0
            auto_memory_budget = False
            memory_budget_raw = server_config.get('memory_budget')
            configured_memory_budget = Capacity(memory_budget_raw).bytes if memory_budget_raw else 0
            if configured_memory_budget > 0:
                memory_limit = configured_memory_budget
                if production_mode and memory_limit < PRO_MEMORY_MIN:
                    error(server, 'mem', err.EC_OBSERVER_PRODUCTION_MODE_LIMIT.format(server=server, key='memory_budget',
                                                                                      limit=str(
                                                                                          Capacity(PRO_MEMORY_MIN))),
                          [err.SUB_SET_NO_PRODUCTION_MODE.format()])
                memory['num'] += memory_limit
            else:
                auto_memory_budget = True
            memory['servers'][server] = {
                'num': memory_limit,
                'percentage': percentage,
                'system_memory': 0,
                'auto_memory_budget': auto_memory_budget,
            }

            data_path = server_config['data_dir'] if server_config.get('data_dir') else os.path.join(
                server_config['home_path'], 'store')
            redo_dir = server_config['redo_dir'] if server_config.get('redo_dir') else os.path.join(data_path, 'redo')
            clog_dir = server_config['clog_dir'] if server_config.get('clog_dir') else redo_dir

            if not client.execute_command('ls %s/sstable/block_file' % data_path):
                disk[data_path] = {'server': server}
                clog_mount[clog_dir] = {'server': server}
                _df = server_config.get('datafile_maxsize') or server_config.get('datafile_size')
                if _df:
                    # if need is string, it means use datafile_maxsize (or legacy datafile_size)
                    disk[data_path]['need'] = _df
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
                    if IS_DARWIN:
                        devname_check_cmd = "ifconfig %s 2>/dev/null" % devname
                    else:
                        devname_check_cmd = "grep -e '^ *%s:' /proc/net/dev" % devname
                    if not client.execute_command(devname_check_cmd):
                        suggest = err.SUG_NO_SUCH_NET_DEVIC.format(ip=ip)
                        suggest.auto_fix = 'devname' not in global_generate_config and 'devname' not in server_generate_config
                        critical(server, 'net', err.EC_NO_SUCH_NET_DEVICE.format(server=server, devname=devname), suggests=[suggest])
                if devname not in interfaces:
                    interfaces[devname] = []
                interfaces[devname].append(ip)
    plugin_context.set_variable('servers_memory', servers_memory)
    plugin_context.set_variable('servers_disk', servers_disk)
    plugin_context.set_variable('servers_clog_mount', servers_clog_mount)
    plugin_context.set_variable('servers_net_interface', servers_net_interface)
    plugin_context.set_variable('servers_min_pool_memory', servers_min_pool_memory)
    return plugin_context.return_true()
