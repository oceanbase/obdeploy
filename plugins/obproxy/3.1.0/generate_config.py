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


def generate_config(plugin_context, deploy_config, auto_depend=False, *args, **kwargs):
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
        cluster_config.update_server_conf(server, 'enable_cluster_checkout', False)
    if not success:
        stdio.stop_loading('fail')
        return

    global_config = cluster_config.get_original_global_conf()
    if 'skip_proxy_sys_private_check' not in global_config:
        cluster_config.update_global_conf('skip_proxy_sys_private_check', True, False)
    if 'enable_strict_kernel_release' not in global_config:
        cluster_config.update_global_conf('enable_strict_kernel_release', False, False)
    
    if getattr(plugin_context.options, 'mini', False):
        if 'proxy_mem_limited' not in global_config:
            cluster_config.update_global_conf('proxy_mem_limited', '200M', False)

    ob_comps = ['oceanbase', 'oceanbase-ce']
    ob_cluster_config = None
    for comp in ob_comps:
        if comp in cluster_config.depends:
            stdio.stop_loading('succeed')
            return plugin_context.return_true()
        if comp in deploy_config.components:
            ob_cluster_config = deploy_config.components[comp]

    if auto_depend:
        for depend in ['oceanbase', 'oceanbase-ce']:
            if cluster_config.add_depend_component(depend):
                stdio.stop_loading('succeed')
                return plugin_context.return_true()

    if ob_cluster_config:
        root_servers = {}
        cluster_name = ob_cluster_config.get_global_conf().get('appname')
        for server in ob_cluster_config.servers:
            config = ob_cluster_config.get_server_conf_with_default(server)
            zone = config['zone']
            cluster_name = cluster_name if cluster_name else config.get('appname')
            if zone not in root_servers:
                root_servers[zone] = '%s:%s' % (server.ip, config['mysql_port'])
        rs_list = ';'.join([root_servers[zone] for zone in root_servers])

        cluster_name = cluster_name if cluster_name else 'obcluster'
        if not global_config.get('rs_list'):
            cluster_config.update_global_conf('rs_list', rs_list, False)
        if not global_config.get('cluster_name'):
            cluster_config.update_global_conf('cluster_name', cluster_name, False)
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()