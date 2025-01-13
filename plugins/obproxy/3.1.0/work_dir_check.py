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


def work_dir_check(plugin_context, work_dir_check=False, work_dir_empty_check=True, *args, **kwargs):

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    servers_dirs = {}
    servers_check_dirs = {}
    running_status = plugin_context.get_variable('running_status')
    critical = plugin_context.get_variable('critical')
    check_pass = plugin_context.get_variable('check_pass')
    success = True

    for server in cluster_config.servers:
        if running_status and running_status.get(server):
            continue

        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
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
                critical(server, 'dir',
                         err.EC_CONFIG_CONFLICT_DIR.format(server1=server, path=path, server2=dirs[path]['server'],
                                                           key=dirs[path]['key']), suggests)
                success = False
            dirs[path] = {
                'server': server,
                'key': key,
            }
            empty_check = work_dir_empty_check
            while True:
                if path in check_dirs:
                    if check_dirs[path] != True:
                        critical(server, 'dir', check_dirs[path], suggests)
                        success = False
                    break

                if client.execute_command('bash -c "[ -a %s ]"' % path):
                    is_dir = client.execute_command('[ -d {} ]'.format(path))
                    has_write_permission = client.execute_command('[ -w {} ]'.format(path))
                    if is_dir and has_write_permission:
                        if empty_check:
                            ret = client.execute_command('ls %s' % path)
                            if not ret or ret.stdout.strip():
                                check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key,
                                                                                   msg=err.InitDirFailedErrorMessage.NOT_EMPTY.format(
                                                                                       path=path))
                            else:
                                check_dirs[path] = True
                        else:
                            check_dirs[path] = True
                    else:
                        if not is_dir:
                            check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key,
                                                                               msg=err.InitDirFailedErrorMessage.NOT_DIR.format(
                                                                                   path=path))
                        else:
                            check_dirs[path] = err.EC_FAIL_TO_INIT_PATH.format(server=server, key=key,
                                                                               msg=err.InitDirFailedErrorMessage.PERMISSION_DENIED.format(
                                                                                   path=path))
                else:
                    path = os.path.dirname(path)
                    empty_check = False
        if work_dir_check and success:
            check_pass(server, 'dir')
    plugin_context.return_true()
