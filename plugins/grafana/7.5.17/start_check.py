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
from tool import OrderedDict
import _errno as err


stdio = None
success = True


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{udp*,tcp*}' | awk -F' ' '{print $2,$10}' | grep '00000000:%s' | awk -F' ' '{print $2}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    return res.stdout.strip().split('\n')


def start_check(plugin_context, init_check_status=False, work_dir_check=False, work_dir_empty_check=True, precheck=False, *args, **kwargs):
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
    def critical(item, error, suggests=[]):
        global success
        success = False
        check_fail(item, error, suggests)
        stdio.error(error)

    global stdio, success
    success = True
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_port = {}
    servers_dirs = {}
    servers_check_dirs = {}
    check_status = {}
    plugin_context.set_variable('start_check_status', check_status)
    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
            'password': err.CheckStatus(),
        }
        if work_dir_check:
             check_status[server]['dir'] = err.CheckStatus()

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before start grafana')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        ip = server.ip
        client = clients[server]
        if not precheck:
            remote_pid_path = os.path.join(home_path, 'run/grafana.pid')
            remote_pid = client.execute_command('cat %s' % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is runnning, skip' % server)
                    wait_2_pass()
                    continue

        if work_dir_check:
            stdio.verbose('%s dir check' % server)       
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            original_server_conf = cluster_config.get_server_conf(server)

            if not server_config.get('data_dir'):
                server_config['data_dir'] = '%s/data' % home_path
            if not server_config.get('logs_dir'):
                server_config['logs_dir'] = '%s/log' % server_config['data_dir']
            if not server_config.get('plugins_dir'):
                server_config['plugins_dir'] = '%s/plugins' % server_config['data_dir']
            if not server_config.get('provisioning_dir'):
                server_config['provisioning_dir'] = '%s/conf/provisioning' % home_path

            keys = ['home_path', 'data_dir','logs_dir', 'plugins_dir', 'provisioning_dir']
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

        if server_config['login_password'] == 'admin':
            critical('password', err.EC_GRAFANA_DEFAULT_PWD.format(server=server), [err.SUG_GRAFANA_PWD.format()])
        elif len(str(server_config['login_password'])) < 5:
            critical('password', err.EC_GRAFANA_PWD_LESS_5.format(server=server), [err.SUG_GRAFANA_PWD.format()])
        else:
            check_pass('password')

        if ip not in servers_port:
            servers_port[ip] = {}
        ports = servers_port[ip]

        stdio.verbose('%s port check' % server)       
        port = server_config['port']
        if port in ports:
            critical(
                'port',
                err.EC_CONFIG_CONFLICT_PORT.format(server1=server, port=port, server2=ports[port]['server'], key=ports[port]['key']),
                [err.SUG_PORT_CONFLICTS.format()]
            )
        else:
            ports[port] = {
                'server': server,
                'key': port
            }
            if get_port_socket_inode(client, port):
                critical(
                    'port', 
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )
                continue
            check_pass('port')

    for server in cluster_config.servers:
        wait_2_pass()
    
    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')