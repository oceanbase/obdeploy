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

import const


def restart(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.get_variable('clients')
    zones_servers = plugin_context.get_variable('zones_servers')
    new_clients = plugin_context.get_variable('new_clients')
    new_deploy_config = plugin_context.get_variable('new_deploy_config')
    new_cluster_config = new_deploy_config.components[kwargs['repository'].name] if new_deploy_config else {}
    component_name = plugin_context.cluster_config.name
    all_servers = cluster_config.servers
    if len(zones_servers) > 2:
        #rolling
        pre_zone = None
        for zone in zones_servers:
            cluster_config.servers = zones_servers[zone]
            if new_cluster_config:
                new_cluster_config.servers = zones_servers[zone]
            workflow.add_with_kwargs(const.STAGE_FIRST, {"cluster_config": cluster_config, "zone": pre_zone}, 'start_zone', "active_check")
            workflow.add_with_kwargs(const.STAGE_FIRST, {"cluster_config": cluster_config, "zone": zone}, "stop_zone", "stop")
            if const.COMP_OB_CE == component_name:
                workflow.add(const.STAGE_FIRST, 'obshell_stop')
            if new_clients:
                workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {"new_clients": new_clients, "cluster_config": cluster_config}, 'chown_dir')
            workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config},
                                     'configserver_pre', 'start_pre', 'start', 'health_check')
            if const.COMP_OB_CE == component_name:
                workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config}, 'obshell_start', 'obshell_bootstrap')
            pre_zone = zone
        workflow.add_with_kwargs(const.STAGE_FIRST, {"cluster_config": cluster_config, "zone": pre_zone}, 'start_zone')
        cluster_config.servers = all_servers
        if new_cluster_config:
            new_cluster_config.servers = all_servers
    else:
        # un_rolling
        workflow.add(const.STAGE_FIRST,  "stop")
        if const.COMP_OB_CE == component_name:
            workflow.add(const.STAGE_FIRST, 'obshell_stop')
        if new_clients:
            workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {"new_clients": new_clients}, 'chown_dir')
        workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config},
                                 'configserver_pre', 'start_pre', 'start', 'health_check')
        if const.COMP_OB_CE == component_name:
            workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config}, 'obshell_start', 'obshell_bootstrap')

    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients}, 'connect')

    finally_plugins = ['display']
    if new_cluster_config:
        workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "new_cluster_config": new_cluster_config, "repository_dir": kwargs.get('repository').repository_dir}, "reload")
        if const.COMP_OB_CE == component_name:
            workflow.add_with_kwargs(const.STAGE_FIRST, {"cluster_config": new_cluster_config}, "obshell_password_reload")
        cluster_config = new_cluster_config
    if new_clients:
        clients = new_clients

    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "new_cluster_config": new_cluster_config, "cursor": None, "repository_dir": kwargs.get('repository').repository_dir}, *finally_plugins)

    return plugin_context.return_true()




