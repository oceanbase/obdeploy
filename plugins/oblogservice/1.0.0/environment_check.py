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

import _errno as err
from tool import check_environment_work_dir

from oblogservice_util import get_store_dir


def environment_check(plugin_context, work_dir_empty_check=True, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    critical = plugin_context.get_variable('critical')
    work_dir_check = plugin_context.get_variable('work_dir_check')
    running_servers = plugin_context.get_variable('running_servers', default=set()) or set()
    if work_dir_empty_check is None:
        work_dir_empty_check = plugin_context.get_variable('work_dir_empty_check', default=True)

    servers_dirs = {}
    for server in cluster_config.servers:
        if server in running_servers:
            continue
        if not work_dir_check:
            continue
        ip = server.ip
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        home_path = server_config['home_path']
        store_path = get_store_dir(home_path)

        stdio.verbose('%s dir check' % server)
        if ip not in servers_dirs:
            servers_dirs[ip] = {}

        dirs = servers_dirs[ip]
        path_items = [
            ('home_path', home_path),
            ('store', store_path),
        ]
        for key, path in path_items:
            suggests = [err.SUG_CONFIG_CONFLICT_DIR.format(key=key, server=server)]
            if path in dirs:
                critical(
                    server,
                    'dir',
                    err.EC_CONFIG_CONFLICT_DIR.format(
                        server1=server,
                        path=path,
                        server2=dirs[path]['server'],
                        key=dirs[path]['key'],
                    ),
                    suggests,
                )
                continue
            dirs[path] = {'server': server, 'key': key}

            dir_err = check_environment_work_dir(
                client,
                server,
                path,
                key=key,
                work_dir_empty_check=work_dir_empty_check,
            )
            if dir_err is not None:
                critical(server, 'dir', dir_err, [err.SUG_SPECIFY_PATH.format()])

    return plugin_context.return_true()
