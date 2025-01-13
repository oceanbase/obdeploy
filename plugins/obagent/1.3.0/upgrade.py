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


def call_plugin(plugin, plugin_context, repositories, *args, **kwargs):
    namespace = plugin_context.namespace
    namespaces = plugin_context.namespaces
    deploy_name = plugin_context.deploy_name
    deploy_status = plugin_context.deploy_status
    components = plugin_context.components
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config
    cmds = plugin_context.cmds
    options = plugin_context.options
    stdio = plugin_context.stdio
    return plugin(namespace, namespaces, deploy_name, deploy_status, repositories, components, clients, cluster_config, cmds, options,
                  stdio, *args, **kwargs)


def upgrade(plugin_context, search_py_script_plugin, apply_param_plugin, install_repository_to_servers, run_workflow, get_workflows, *args, **kwargs):

    def summit_config():
        generate_global_config = generate_configs['global']
        for key in generate_global_config:
            cluster_config.update_global_conf(key, generate_global_config[key], False)
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_server_config = generate_configs[server]
            for key in generate_server_config:
                cluster_config.update_server_conf(server, key, generate_server_config[key], False)

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
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

    apply_param_plugin(cur_repository)
    if not run_workflow(stop_workflows, repositories=[cur_repository], **kwargs):
        return
    install_repository_to_servers(cluster_config.name, cluster_config, dest_repository, clients)
    # clean useless config
    clean_files = [
        "conf/config_properties/monagent_basic_auth.yaml",
        "conf/module_config/monitor_mysql.yaml",
        "conf/module_config/monagent_config.yaml",
        "conf/module_config/monitor_ob_log.yaml"
    ]
    for server in cluster_config.servers:
        client = clients[server]
        home_path = cluster_config.get_server_conf(server)['home_path']
        for f in clean_files:
            client.execute_command('rm -f {0}'.format(os.path.join(home_path, f)))

    # update port
    generate_configs = {"global": {}}
    original_global_config = cluster_config.get_original_global_conf()
    port_keys = {
        'server_port': 'monagent_http_port',
        'pprof_port': 'mgragent_http_port'
    }
    port_warns = {}
    for server in cluster_config.servers:
        original_server_config = cluster_config.get_original_server_conf(server)
        server_config = cluster_config.get_server_conf(server)
        for port_key in port_keys:
            if port_key in original_global_config or port_key in original_server_config:
                port = server_config[port_key]
                if server not in generate_configs:
                    generate_configs[server] = {}
                generate_configs[server][port_keys[port_key]] = port
                if port_key not in port_warns:
                    port_warns[port_key] = 'Configuration item {} is no longer supported, and it is converted to configuration item {}'.format(port_key, port_keys[port_key])
    if port_warns:
        for msg in port_warns.values():
            stdio.warn(msg)
    # merge_generate_config
    merge_config = {}
    generate_global_config = generate_configs['global']
    count_base = len(cluster_config.servers) - 1
    if count_base < 1:
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_global_config.update(generate_configs[server])
            generate_configs[server] = {}
    else:
        for server in cluster_config.servers:
            if server not in generate_configs:
                continue
            generate_server_config = generate_configs[server]
            merged_server_config = {}
            for key in generate_server_config:
                if key in generate_global_config:
                    if generate_global_config[key] != generate_server_config[key]:
                        merged_server_config[key] = generate_server_config[key]
                elif key in merge_config:
                    if merge_config[key]['value'] != generate_server_config[key]:
                        merged_server_config[key] = generate_server_config[key]
                    elif count_base == merge_config[key]['count']:
                        generate_global_config[key] = generate_server_config[key]
                        del merge_config[key]
                    else:
                        merge_config[key]['severs'].append(server)
                        merge_config[key]['count'] += 1
                else:
                    merge_config[key] = {'value': generate_server_config[key], 'severs': [server], 'count': 1}
            generate_configs[server] = merged_server_config

        for key in merge_config:
            config_st = merge_config[key]
            for server in config_st['severs']:
                if server not in generate_configs:
                    continue
                generate_server_config = generate_configs[server]
                generate_server_config[key] = config_st['value']
    # summit_config
    summit_config()

    apply_param_plugin(dest_repository)
    if not run_workflow(start_workflows, repositories=[dest_repository], **kwargs):
        return
    
    ret = call_plugin(connect_plugin, plugin_context,  [dest_repository], *args, **kwargs)
    if ret and call_plugin(display_plugin, plugin_context, [dest_repository], ret.get_return('cursor'), *args, **kwargs):
        upgrade_ctx['index'] = len(upgrade_repositories)
        return plugin_context.return_true()
