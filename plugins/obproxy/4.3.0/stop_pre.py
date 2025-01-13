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
        server_config = cluster_config.get_server_conf(server)
        servers_pid_filenames[server] = ['obproxyd-%s-%s.pid' % (server.ip, server_config["listen_port"]), 'obproxy-%s-%s.pid' % (server.ip, server_config["listen_port"])]

    plugin_context.set_variable('servers_pid_filenames', servers_pid_filenames)
    plugin_context.set_variable('port_keys', ['prometheus_listen_port', 'listen_port', 'rpc_listen_port'])
    return plugin_context.return_true()