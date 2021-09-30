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
    have_depend = False
    depends = ['oceanbase', 'oceanbase-ce']
    server_depends = {}
    stdio.start_loading('Generate obagent configuration')

    for server in cluster_config.servers:
        server_depends[server] = []
        server_config = cluster_config.get_server_conf(server)
        if not server_config.get('home_path'):
            stdio.error("obagent %s: missing configuration 'home_path' in configuration file" % server)
            success = False
            continue
    if not success:
        stdio.stop_loading('fail')
        return

    for comp in cluster_config.depends:
        if comp in depends:
            have_depend = True
            for server in cluster_config.servers:
                obs_config = cluster_config.get_depled_config(comp, server)
                if obs_config is not None:
                    server_depends[server].append(comp)
    
    if have_depend:
        server_num = len(cluster_config.servers)
        for server in cluster_config.servers:
            for comp in depends:
                if comp in server_depends[server]:
                    break
            else:
                cluster_config.update_server_conf(server, 'ob_monitor_status', 'inactive', False)
    else:
        cluster_config.update_global_conf('ob_monitor_status', 'inactive', False)

    stdio.stop_loading('succeed')
    plugin_context.return_true()
