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
from _rpm import Version

from tool import get_port_socket_inode
from const import COMP_OBBINLOG_CE, COMP_OBBINLOG, COMP_OB, COMP_OB_CE, COMP_OB_STANDALONE, COMPS_ODP, COMPS_OB


stdio = None
success = True


def start_check(plugin_context, init_check_status=False, strict_check=False, work_dir_check=False, work_dir_empty_check=True, precheck=False, *args, **kwargs):
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
            stdio.error(error)
        else:
            stdio.warn(error)
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
    check_status = {}
    servers_dirs = {}
    servers_check_dirs = {}

    for server in cluster_config.servers:
        check_status[server] = {
            'port': err.CheckStatus(),
            'oceanbase version': err.CheckStatus(),
            'obproxy version': err.CheckStatus()
        }
        if work_dir_check:
            check_status[server]['dir'] = err.CheckStatus()
        for comp in COMPS_OB:
            if comp in cluster_config.depends:
                check_status[server]['username'] = err.CheckStatus()
                check_status[server]['password'] = err.CheckStatus()

    plugin_context.set_variable('start_check_status', check_status)
    if init_check_status:
        return plugin_context.return_true(start_check_status=check_status)

    stdio.verbose('oceanbase version check')
    versions_check = {
        "oceanbase version": {
            'comps': COMPS_OB,
            'min_version': Version('4.2.1')
        },
        "obproxy version": {
            'comps': COMPS_ODP,
            'min_version': Version('4.2.1')
        }
    }

    repo_versions = {}
    for repository in plugin_context.repositories:
        repo_versions[repository.name] = repository.version

    binlog_repository = kwargs.get('repository')
    depends = cluster_config.depends
    if binlog_repository.name == COMP_OBBINLOG_CE and (COMP_OB in depends or COMP_OB_STANDALONE in depends):
        critical("oceanbase version", err.EC_OBBINLOG_CE_WITH_OCENABASE_CE)
    if binlog_repository.name == COMP_OBBINLOG and COMP_OB_CE in depends:
        critical("oceanbase version", err.EC_OBBINLOG_WITH_OCENABASE)

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
                critical(check_item, err.EC_OBLOGPROXY_DEPENDS_COMP_VERSION.format(oblogproxy_version=cluster_config.version, comp=comp, comp_version=min_version))
    
    global_config = cluster_config.get_original_global_conf()
    for comp in COMPS_OB:
        if comp in cluster_config.depends:
            for key in ['ob_sys_username', 'ob_sys_password']:
                if key in global_config:
                    alert(
                        key,
                        err.WC_PARAM_USELESS.format(key=key, current_comp=cluster_config.name, comp=comp),
                        [err.SUG_OB_SYS_USERNAME.format()]
                    )

    for server in cluster_config.servers:
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        ports = [int(server_config["service_port"]), int(server_config['prometheus_port'])]
        if not precheck:
            remote_pid_path = "%s/run/%s-%s-%s.pid" % (server_config['home_path'], cluster_config.name, server.ip, server_config["service_port"])
            remote_pid = client.execute_command("cat %s" % remote_pid_path).stdout.strip()
            if remote_pid:
                if client.execute_command('ls /proc/%s/fd' % remote_pid):
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
            keys = ['home_path', 'binlog_dir']
            for key in keys:
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

        stdio.verbose('%s port check' % server)
        for port in ports:
            if get_port_socket_inode(client, port):
                critical(
                    'port',
                    err.EC_CONFLICT_PORT.format(server=ip, port=port),
                    [err.SUG_USE_OTHER_PORT.format()]
                )

    for server in cluster_config.servers:
        wait_2_pass()

    if success:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')