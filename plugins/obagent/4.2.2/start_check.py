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
from copy import deepcopy

import _errno as err
from tool import YamlLoader, FileUtil


stdio = None
success = True

OBAGNET_CONFIG_MAP = {
    "monitor_password": "{ocp_agent_monitor_password}",
    "monitor_user": "{ocp_agent_monitor_username}",
    "sql_port": "{mysql_port}",
    "rpc_port": "{rpc_port}",
    "cluster_name": "{appname}",
    "cluster_id": "{cluster_id}",
    "zone_name": "{zone}",
    "ob_log_path": "{home_path}/store",
    "ob_data_path": "{home_path}/store",
    "ob_install_path": "{home_path}",
    "observer_log_path": "{home_path}/log",
}


def get_missing_required_parameters(parameters):
    results = []
    for key in OBAGNET_CONFIG_MAP:
        if parameters.get(key) is None:
            results.append(key)
    return results


def get_port_socket_inode(client, port):
    port = hex(port)[2:].zfill(4).upper()
    cmd = "bash -c 'cat /proc/net/{tcp*,udp*}' | awk -F' ' '{if($4==\"0A\") print $2,$4,$10}' | grep ':%s' | awk -F' ' '{print $3}' | uniq" % port
    res = client.execute_command(cmd)
    if not res or not res.stdout.strip():
        return False
    stdio.verbose(res.stdout)
    return res.stdout.strip().split('\n')


def prepare_parameters(cluster_config):
    env = {}
    depend_info = {}
    ob_servers_config = {}
    depends_keys = ["ocp_agent_monitor_username", "ocp_agent_monitor_password", "appname", "cluster_id"]
    for comp in ["oceanbase", "oceanbase-ce"]:
        if comp in cluster_config.depends:
            observer_globals = cluster_config.get_depend_config(comp)
            for key in depends_keys:
                value = observer_globals.get(key)
                if value is not None:
                    depend_info[key] = value
            ob_servers = cluster_config.get_depend_servers(comp)
            for server in ob_servers:
                ob_servers_config[server] = cluster_config.get_depend_config(comp, server)

    for server in cluster_config.servers:
        server_config = deepcopy(cluster_config.get_server_conf_with_default(server))
        user_server_config = deepcopy(cluster_config.get_server_conf(server))
        if 'monagent_host_ip' not in user_server_config:
            server_config['monagent_host_ip'] = server.ip
        missed_keys = get_missing_required_parameters(user_server_config)
        if missed_keys and server in ob_servers_config:
            for key in depend_info:
                ob_servers_config[server][key] = depend_info[key]
            for key in missed_keys:
                server_config[key] = OBAGNET_CONFIG_MAP[key].format(server_ip=server.ip, **ob_servers_config[server])
        env[server] = server_config
    return env


def password_check(password):
    if not re.match(r'^[\w~^*{}\[\]_\-+]+$', password):
        return False
    return True


def start_check(plugin_context, init_check_status=False, strict_check=False, work_dir_check=False, work_dir_empty_check=True, precheck=False, *args, **kwargs):
    def check_fail(item, error, suggests=[]):
        status = check_status[server][item]
        if status.status == err.CheckStatus.WAIT:
            status.error = error
            status.suggests = suggests
            status.status = err.CheckStatus.FAIL

    def alert(item, error, suggests=[]):
        global success
        if strict_check:
            success = False
            check_fail(item, error, suggests)
            stdio.error(error)
        else:
            stdio.warn(error)

    def critical(item, error, suggests=[]):
        global success
        success = False
        status = check_status.get(server).get(item)
        status.status = err.CheckStatus.FAIL
        status.error = error
        status.suggests = suggests
        stdio.error(error)

    def check_pass(item):
        status = check_status.get(server).get(item).status
        if status == err.CheckStatus.WAIT:
            check_status.get(server).get(item).status = err.CheckStatus.PASS

    def wait_2_pass():
        status = check_status[server]
        for key in status:
            if status[key].status == err.CheckStatus.WAIT:
                status[key].status = err.CheckStatus.PASS

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
            'parameter': err.CheckStatus(),
            'password': err.CheckStatus()
        }
        if work_dir_check:
             check_status[server]['dir'] = err.CheckStatus()

    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.start_loading('Check before start obagent')
    env = prepare_parameters(cluster_config)
    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        if not precheck:
            remote_pid_path = "%s/run/ob_agentd.pid" % server_config['home_path']
            remote_pid = client.execute_command("cat %s" % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s' % remote_pid):
                    stdio.verbose('%s is runnning, skip' % server)
                    wait_2_pass()
                    continue
        check_pass('parameter')

        # http_basic_auth_password check
        http_basic_auth_password = server_config.get('http_basic_auth_password')
        if http_basic_auth_password:
            if not password_check(http_basic_auth_password):
                critical('password', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='obagent', key='http_basic_auth_password', rule='^[\w~^*{}\[\]_\-+]+$'), suggests=[err.SUG_OBAGENT_EDIT_HTTP_BASIC_AUTH_PASSWORD.format()])

        if work_dir_check:
            stdio.verbose('%s dir check' % server)
            if ip not in servers_dirs:
                servers_dirs[ip] = {}
                servers_check_dirs[ip] = {}
            dirs = servers_dirs[ip]
            check_dirs = servers_check_dirs[ip]
            key = 'home_path'
            path = server_config.get(key)
            suggests = [err.SUG_CONFIG_CONFLICT_DIR.format(key=key, server=server)]
            if path in dirs and dirs[path]:
                critical('dir', err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'], key=dirs[path]['key']), suggests)
            dirs[path] = {
                'server': server,
                'key': key,
            }
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
            servers_port[ip] = {}
        ports = servers_port[ip]

        stdio.verbose('%s port check' % server)
        for key in ['mgragent_http_port', 'monagent_http_port']:
            port = int(server_config[key])
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
                critical(
                    'port',
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )
        check_pass('port')
    plugin_context.set_variable('start_env', env)

    for server in cluster_config.servers:
        wait_2_pass()


    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')