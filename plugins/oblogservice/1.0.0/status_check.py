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

from oblogservice_util import detect_running_servers


def status_check(plugin_context, precheck=False, *args, **kwargs):
    if precheck:
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    wait_2_pass = plugin_context.get_variable('wait_2_pass')

    running_servers = detect_running_servers(cluster_config, clients, stdio)
    for server in running_servers:
        wait_2_pass(server)

    plugin_context.set_variable('running_servers', running_servers)
    return plugin_context.return_true()
