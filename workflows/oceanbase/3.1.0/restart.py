# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import const


def restart(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.get_variable('clients')
    zones_servers = plugin_context.get_variable('zones_servers')
    new_clients = plugin_context.get_variable('new_clients')
    new_deploy_config = plugin_context.get_variable('new_deploy_config')
    new_cluster_config = new_deploy_config.components[kwargs['repository'].name] if new_deploy_config else {}
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
            if new_clients:
                workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {"new_clients": new_clients, "cluster_config": cluster_config}, 'chown_dir')
            workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config},
                                     'configserver_pre', 'start_pre', 'start', 'health_check')
            pre_zone = zone
        workflow.add_with_kwargs(const.STAGE_FIRST, {"cluster_config": cluster_config, "zone": pre_zone}, 'start_zone')
        cluster_config.servers = all_servers
        if new_cluster_config:
            new_cluster_config.servers = all_servers
    else:
        # un_rolling
        workflow.add(const.STAGE_FIRST,  "stop")
        if new_clients:
            workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {"new_clients": new_clients}, 'chown_dir')
        workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients, "new_cluster_config": new_cluster_config, "cluster_config": new_cluster_config if new_cluster_config else cluster_config},
                                 'configserver_pre', 'start_pre', 'start', 'health_check')

    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": new_clients if new_clients else clients}, 'connect')

    finally_plugins = ['display']
    if new_cluster_config:
        workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "new_cluster_config": new_cluster_config, "repository_dir": kwargs.get('repository').repository_dir}, "reload")
        cluster_config = new_cluster_config
    if new_clients:
        clients = new_clients

    workflow.add_with_kwargs(const.STAGE_FIRST, {"clients": clients, "cluster_config": cluster_config, "new_cluster_config": new_cluster_config, "cursor": None, "repository_dir": kwargs.get('repository').repository_dir}, *finally_plugins)

    return plugin_context.return_true()




