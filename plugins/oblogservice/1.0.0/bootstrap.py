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
    OBLOGSERVICE_MIN_SERVERS,
    bootstrap_marker_path,
    build_bootstrap_cmd,
    get_bootstrap_server,
    http_addr,
    rpc_addr,
    should_skip_bootstrap,
)


def bootstrap(plugin_context, *args, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    if need_bootstrap is False:
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_conf = cluster_config.get_global_conf()
    if should_skip_bootstrap(global_conf):
        stdio.verbose('skip oblogservice bootstrap (skip_bootstrap or no valid object_store_url)')
        return plugin_context.return_true()

    object_store_url = global_conf.get('object_store_url')
    if not object_store_url:
        stdio.error('object_store_url is required for oblogservice bootstrap')
        return plugin_context.return_false()

    server_count = len(cluster_config.servers)
    if server_count < OBLOGSERVICE_MIN_SERVERS:
        stdio.error(
            'oblogservice bootstrap requires at least %d nodes, got %d'
            % (OBLOGSERVICE_MIN_SERVERS, server_count)
        )
        return plugin_context.return_false()

    server_specs = []
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf_with_default(server)
        server_specs.append((
            server_config['region'],
            server_config['az'],
            rpc_addr(server, server_config),
        ))

    bootstrap_server = get_bootstrap_server(cluster_config)
    if bootstrap_server is None:
        stdio.error(err.EC_OBLOGSERVICE_INVALID_BOOTSTRAP_SERVER.format(
            bootstrap_server=global_conf.get('bootstrap_server')))
        return plugin_context.return_false()
    bootstrap_conf = cluster_config.get_server_conf_with_default(bootstrap_server)
    client = clients[bootstrap_server]
    home_path = bootstrap_conf['home_path']
    http_host = http_addr(bootstrap_server, bootstrap_conf)
    marker = bootstrap_marker_path(home_path)

    if client.execute_command('[ -f %s ]' % marker).code == 0:
        stdio.verbose('oblogservice cluster already bootstrapped, skip')
        return plugin_context.return_true()

    stdio.start_loading('bootstrap oblogservice cluster')
    cmd = build_bootstrap_cmd(home_path, http_host, object_store_url, server_specs)
    stdio.verbose('bootstrap cmd: %s' % cmd)
    ret = client.execute_command(cmd, timeout=600)
    output = (ret.stdout or '') + (ret.stderr or '')
    if ret.code != 0 or '200' not in output:
        stdio.stop_loading('fail')
        stdio.error('oblogservice bootstrap failed: %s' % output.strip())
        return plugin_context.return_false()
    if 'lm_leader' not in output and '"data"' not in output:
        stdio.warn('bootstrap returned 200 but lm_leader not found in output, please verify manually')

    client.execute_command('touch %s' % marker)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
