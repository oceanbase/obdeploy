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