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


def sync_cluster_config(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            root_servers = {}
            ob_config = cluster_config.get_depend_config(comp)
            if not ob_config:
                continue
            odp_config = cluster_config.get_global_conf()
            for server in cluster_config.get_depend_servers(comp):
                config = cluster_config.get_depend_config(comp, server)
                zone = config['zone']
                if zone not in root_servers:
                    root_servers[zone] = '%s:%s' % (server.ip, config['mysql_port'])
            depend_rs_list = ';'.join([root_servers[zone] for zone in root_servers])
            cluster_config.update_global_conf('rs_list', depend_rs_list, save=False)

            config_map = {
                'observer_sys_password': 'proxyro_password',
                'cluster_name': 'appname',
                'observer_root_password': 'root_password'
            }
            for key in config_map:
                ob_key = config_map[key]
                if not odp_config.get(key) and ob_config.get(ob_key):
                    stdio.verbose("update config, key: {}, value: {}".format(key, ob_config.get(ob_key)))
                    cluster_config.update_global_conf(key, ob_config.get(ob_key), save=False)
            break

    return plugin_context.return_true()