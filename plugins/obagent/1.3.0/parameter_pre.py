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


def parameter_pre(plugin_context, **kwargs):
    def get_missing_required_parameters(parameters):
        results = []
        for key in OBAGNET_CONFIG_MAP:
            if parameters.get(key) is None:
                results.append(key)
        return results

    def prepare_parameters(cluster_config):
        env = {}
        depend_info = {}
        ob_servers_config = {}
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

    OBAGNET_CONFIG_MAP = plugin_context.get_variable('OBAGNET_CONFIG_MAP')
    depends_keys = plugin_context.get_variable('depends_keys')
    cluster_config = plugin_context.cluster_config
    env = prepare_parameters(cluster_config)
    if not env:
        return plugin_context.return_false()

    plugin_context.set_variable('start_env', env)
    return plugin_context.return_true()
