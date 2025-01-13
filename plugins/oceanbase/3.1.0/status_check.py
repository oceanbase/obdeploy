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

from tool import set_plugin_context_variables


success = False


def status_check(plugin_context, work_dir_check=False, precheck=False, source_option='start', *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    wait_2_pass = plugin_context.get_variable('wait_2_pass')

    parameter_check = True
    port_check = True
    kernel_check = True
    servers_clients = {}
    servers_port = {}
    servers_memory = {}
    servers_disk = {}
    servers_clog_mount = {}
    servers_net_interface = {}
    is_running_opt = source_option in ['restart', 'upgrade']
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        servers_clients[ip] = client
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        if not precheck:
            remote_pid_path = '%s/run/observer.pid' % home_path
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is runnning, skip' % server)
                    wait_2_pass(server)
                    work_dir_check = False
                    port_check = False
                    parameter_check = False
                    kernel_check = is_running_opt
        if ip not in servers_port:
            servers_disk[ip] = {}
            servers_port[ip] = {}
            servers_clog_mount[ip] = {}
            servers_net_interface[ip] = {}
            servers_memory[ip] = {'num': 0, 'percentage': 0, 'servers': {}}
    variables_dict = {
        'servers_clients': servers_clients,
        'parameter_check': parameter_check,
        'port_check': port_check,
        'kernel_check': kernel_check,
        'work_dir_check': work_dir_check,
        'servers_port': servers_port,
        'servers_disk': servers_disk,
        'servers_clog_mount': servers_clog_mount,
        'servers_net_interface': servers_net_interface,
        'servers_memory': servers_memory
    }
    set_plugin_context_variables(plugin_context, variables_dict)

    return plugin_context.return_true()