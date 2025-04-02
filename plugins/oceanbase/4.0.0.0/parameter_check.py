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

import _errno as err
from _types import Capacity


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

        memory = servers_memory[ip]
        disk = servers_disk[ip]
        clog_mount = servers_clog_mount[ip]
        interfaces = servers_net_interface[ip]
        production_mode = server_config.get('production_mode', False)

        if parameter_check:
            servers_min_pool_memory[server] = __min_full_resource_pool_memory = server_config.get('__min_full_resource_pool_memory')
            if production_mode and __min_full_resource_pool_memory < PRO_POOL_MEM_MIN:
                error(server, 'mem',err.EC_OBSERVER_PRODUCTION_MODE_LIMIT.format(server=server, key="__min_full_resource_pool_memory",limit=PRO_POOL_MEM_MIN), [err.SUB_SET_NO_PRODUCTION_MODE.format()])
            memory_limit = 0
            percentage = 0
            if server_config.get('memory_limit'):
                if memory_limit < PRO_MEMORY_MIN:
                    production_mode = False
                memory_limit = Capacity(server_config['memory_limit']).bytes
                if production_mode and memory_limit < PRO_MEMORY_MIN:
                    error(server, 'mem', err.EC_OBSERVER_PRODUCTION_MODE_LIMIT.format(server=server, key='memory_limit',
                                                                                      limit=str(
                                                                                          Capacity(PRO_MEMORY_MIN))),
                          [err.SUB_SET_NO_PRODUCTION_MODE.format()])
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

            data_path = server_config['data_dir'] if server_config.get('data_dir') else os.path.join(
                server_config['home_path'], 'store')
            redo_dir = server_config['redo_dir'] if server_config.get('redo_dir') else data_path
            clog_dir = server_config['clog_dir'] if server_config.get('clog_dir') else os.path.join(redo_dir, 'clog')

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
