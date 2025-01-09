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


def merge_config(plugin_context, auto_depend=False, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    generate_configs = plugin_context.get_variable('generate_configs')
    success = plugin_context.get_variable('success')
    summit_config = plugin_context.get_variable('summit_config')
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

    if auto_depend and 'ob-configserver' in plugin_context.components and 'ob-configserver' not in cluster_config.depends:
        cluster_config.add_depend_component('ob-configserver')

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    stdio.stop_loading('fail')
    return plugin_context.return_false()