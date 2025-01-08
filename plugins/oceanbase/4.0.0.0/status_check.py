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
    ocp_need_bootstrap = True
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
            data_dir = server_config['data_dir'] if server_config.get('data_dir') else '%s/store' % home_path
            if client.execute_command('ls %s/clog/tenant_1/' % data_dir).stdout.strip():
                ocp_need_bootstrap = False
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
        'servers_memory': servers_memory,
        'ocp_need_bootstrap': ocp_need_bootstrap
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()