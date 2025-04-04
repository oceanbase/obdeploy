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


def collect_log(plugin_context, env, test_name=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    if not env.get('collect_log', False):
        stdio.verbose('collect_log is False')
        return

    if test_name is None:
        case_results = env.get('case_results', [])
        if case_results:
            test_name = case_results[-1].get('name')
    if test_name is None:
        stdio.verbose('Undefined: test_name')
        return
    log_pattern = env.get('log_pattern', '*.log')
    if not env.get('log_dir'):
        log_dir = os.path.join(env['var_dir'], 'log')
    else:
        log_dir = env['log_dir']

    is_obproxy = env["component"].startswith("obproxy")
    ob_component = env["component"]

    if is_obproxy:
        intersection = list({'oceanbase', 'oceanbase-ce', 'oceanbase-standalone'}.intersection(set(cluster_config.depends)))
        if not intersection:
            stdio.warn('observer config not in the depends.')
            return
        ob_component = intersection[0]
        ob_services = cluster_config.get_depend_servers(ob_component)
        proxy_services = cluster_config.servers
    else:
        ob_services = cluster_config.servers
        proxy_services = []
    collect_components = env.get('collect_components')
    if not collect_components:
        collect_components = [ob_component]
    else:
        collect_components = collect_components.split(',')
    if ob_component in collect_components:
        for server in ob_services:
            if is_obproxy:
                server_config = cluster_config.get_depend_config(ob_component, server)
            else:
                server_config = cluster_config.get_server_conf(server)
            ip = server.ip
            port = server_config.get('mysql_port', 0)
            client = clients[server]
            home_path = server_config['home_path']
            remote_path = os.path.join(home_path, 'log', log_pattern)
            local_path = os.path.join(log_dir, test_name, '{}:{}'.format(ip, port))
            stdio.start_loading('Collect log for {}'.format(server.name))
            sub_io = stdio.sub_io()
            client.get_dir(local_path, os.path.join(home_path, 'core.*'), stdio=sub_io)
            if client.get_dir(local_path, remote_path, stdio=sub_io):
                stdio.stop_loading('succeed')
            else:
                stdio.stop_loading('fail')
                return plugin_context.return_false()
    if 'obproxy' in collect_components:
        if not is_obproxy:
            stdio.warn('No obproxy detected.')
            return
        for server in proxy_services:
            server_config = cluster_config.get_server_conf(server)
            ip = server.ip
            port = server_config.get('listen_port', 0)
            client = clients[server]
            home_path = server_config['home_path']
            remote_path = os.path.join(home_path, 'log')
            local_path = os.path.join(log_dir, test_name, '{}:{}'.format(ip, port))
            stdio.start_loading('Collect obproxy log for {}'.format(server.name))
            if client.get_dir(local_path, remote_path):
                stdio.stop_loading('succeed')
            else:
                stdio.stop_loading('fail')
                return plugin_context.return_false()
    return plugin_context.return_true()