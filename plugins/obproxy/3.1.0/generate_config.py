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


def generate_config(plugin_context, deploy_config, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    success = True
    stdio.start_loading('Generate obproxy configuration')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        if not server_config.get('home_path'):
            stdio.error("obproxy %s: missing configuration 'home_path' in configuration file" % server)
            success = False
            continue
    if not success:
        stdio.stop_loading('fail')
        return

    global_config = cluster_config.get_global_conf()
    if global_config.get('enable_cluster_checkout') is None:
        cluster_config.update_global_conf('enable_cluster_checkout', False)

    have_depend = False
    depends = ['oceanbase', 'oceanbase-ce']

    for comp in depends:
        if comp in deploy_config.components:
            deploy_config.add_depend_for_component('obagent', comp, False)
            have_depend = True
            break
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()