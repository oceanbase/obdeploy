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

from copy import deepcopy

from _errno import EC_OBSERVER_FAIL_TO_START_WITH_ERR
from tool import EnvVariables


def start(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    clusters_cmd = plugin_context.get_variable('clusters_cmd')
    stdio.start_loading('Start observer')
    for server in clusters_cmd:
        environments = deepcopy(cluster_config.get_environments())
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('starting %s observer', server)
        if 'LD_LIBRARY_PATH' not in environments:
            environments['LD_LIBRARY_PATH'] = '%s/lib:' % server_config['home_path']
        with EnvVariables(environments, client):
            ret = client.execute_command(clusters_cmd[server])
        if not ret:
            stdio.stop_loading('fail')
            stdio.error(EC_OBSERVER_FAIL_TO_START_WITH_ERR.format(server=server, stderr=ret.stderr))
            return
    stdio.stop_loading('succeed')

    need_bootstrap = plugin_context.get_variable('need_bootstrap', False)
    stdio.verbose('need_bootstrap: %s' % need_bootstrap)
    return plugin_context.return_true()
