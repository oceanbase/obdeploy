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

from oblogservice_util import (
    bootstrap_marker_path,
    detect_running_servers,
    get_bootstrap_server,
    should_skip_bootstrap,
)


def start_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_conf = cluster_config.get_global_conf()
    running_servers = detect_running_servers(cluster_config, clients, stdio)
    plugin_context.set_variable('running_servers', running_servers)

    if should_skip_bootstrap(global_conf):
        stdio.verbose('skip bootstrap: skip_bootstrap or placeholder object_store_url')
        plugin_context.set_variable('need_bootstrap', False)
        return plugin_context.return_true()

    bootstrap_server = get_bootstrap_server(cluster_config)
    if bootstrap_server is None:
        stdio.error(err.EC_OBLOGSERVICE_INVALID_BOOTSTRAP_SERVER.format(
            bootstrap_server=global_conf.get('bootstrap_server')))
        return plugin_context.return_false()
    server_config = cluster_config.get_server_conf(bootstrap_server)
    client = clients[bootstrap_server]
    marker = bootstrap_marker_path(server_config['home_path'])
    need_bootstrap = client.execute_command('[ ! -f %s ]' % marker).code == 0
    plugin_context.set_variable('need_bootstrap', need_bootstrap)
    return plugin_context.return_true()
