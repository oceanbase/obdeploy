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

import random
from copy import copy


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, install_repository_to_servers, run_workflow, get_workflows, *args, **kwargs):
    namespace = plugin_context.namespace
    namespaces = plugin_context.namespaces
    deploy_name = plugin_context.deploy_name
    deploy_status = plugin_context.deploy_status
    repositories = plugin_context.repositories
    plugin_name = plugin_context.plugin_name

    components = plugin_context.components
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    cmds = plugin_context.cmds
    options = plugin_context.options
    dev_mode = plugin_context.dev_mode
    stdio = plugin_context.stdio

    upgrade_ctx = kwargs.get('upgrade_ctx')
    local_home_path = kwargs.get('local_home_path')
    upgrade_repositories = kwargs.get('upgrade_repositories')

    cur_repository = upgrade_repositories[0]
    dest_repository = upgrade_repositories[-1]
    repository_dir = dest_repository.repository_dir
    kwargs['repository_dir'] = repository_dir

    stop_workflows = get_workflows('stop', repositories=[cur_repository])
    start_workflows = get_workflows('upgrade_start', repositories=[dest_repository])
    connect_plugin = search_py_script_plugin([dest_repository], 'connect')[dest_repository]
    display_plugin = search_py_script_plugin([dest_repository], 'display')[dest_repository]
    bootstrap_plugin = search_py_script_plugin([dest_repository], 'bootstrap')[dest_repository]

    apply_param_plugin(cur_repository)
    if not run_workflow(stop_workflows, repositories=[cur_repository], **kwargs):
        return
    install_repository_to_servers(cluster_config.name, cluster_config, dest_repository, clients)

    random_num = random.randint(1, 8191 - len(cluster_config.servers))
    num = 0
    global_config = cluster_config.get_original_global_conf()
    if 'enable_obproxy_rpc_service' not in global_config:
        cluster_config.update_global_conf('enable_obproxy_rpc_service', False, False)
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client_session_id_version = server_config.get('client_session_id_version', None)

        if client_session_id_version in [None, 2]:
            cluster_config.update_server_conf('client_session_id_version', 2, False)
            if server_config.get('proxy_id', None) is None:
                cluster_config.update_server_conf(server, 'proxy_id', random_num + num, False)
            num += 1

    apply_param_plugin(dest_repository)
    start_kwargs = copy(kwargs)
    start_kwargs['bootstrap'] = True
    if not run_workflow(start_workflows, repositories=[dest_repository], **{dest_repository.name: start_kwargs}):
        return

    ret = connect_plugin(namespace, namespaces, deploy_name, deploy_status, repositories, components, clients, cluster_config, cmds, options, stdio, *args, **kwargs)
    if ret:
        if bootstrap_plugin(namespace, namespaces, deploy_name, deploy_status, repositories, components, clients, cluster_config, cmds, options, stdio, ret.get_return('cursor'), *args, **kwargs) and display_plugin(namespace, namespaces, deploy_name, deploy_status, repositories, components, clients, cluster_config, cmds, options, stdio, ret.get_return('cursor'), *args, **kwargs):
            upgrade_ctx['index'] = len(upgrade_repositories)
            return plugin_context.return_true()
