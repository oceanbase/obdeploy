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


def stop_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    servers_pid_filenames = {}
    for server in cluster_config.servers:
        servers_pid_filenames[server] = ['ob_agentd.pid', 'ob_monagent.pid', 'ob_mgragent.pid']

    plugin_context.set_variable('port_keys', ['monagent_http_port', 'mgragent_http_port'])
    plugin_context.set_variable('servers_pid_filenames', servers_pid_filenames)
    return plugin_context.return_true()