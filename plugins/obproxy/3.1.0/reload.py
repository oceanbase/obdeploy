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


def reload(plugin_context, cursor, new_cluster_config, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    cluster_server = {}
    change_conf = {}
    global_change_conf = {}
    global_ret = True

    config_map = {
        'observer_sys_password': 'proxyro_password',
        'cluster_name': 'appname'
    }
    for comp in ['oceanbase', 'oceanbase-ce']:
        if comp in cluster_config.depends:
            root_servers = {}
            ob_config = cluster_config.get_depled_config(comp)
            new_ob_config = new_cluster_config.get_depled_config(comp)
            ob_config = {} if ob_config is None else ob_config
            new_ob_config = {} if new_ob_config is None else new_ob_config
            for key in config_map:
                if ob_config.get(key) != new_ob_config.get(key):
                    global_change_conf[config_map[key]] = new_ob_config.get(key)

    for server in servers:
        change_conf[server] = {}
        stdio.verbose('get %s old configuration' % (server))
        config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s new configuration' % (server))
        new_config = new_cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s cluster address' % (server))
        cluster_server[server] = '%s:%s' % (server.ip, config['listen_port'])
        stdio.verbose('compare configuration of %s' % (server))
        for key in new_config:
            if key not in config or config[key] != new_config[key]:
                change_conf[server][key] = new_config[key]
                if key not in global_change_conf:
                    global_change_conf[key] = 1
                else:
                    global_change_conf[key] += 1
                    
    servers_num = len(servers)
    stdio.verbose('apply new configuration')
    success_conf = {}
    sql = ''
    value = None
    for key in global_change_conf:
        success_conf[key] = []
        for server in servers:
            if key not in change_conf[server]:
                continue
            try:
                sql = 'alter proxyconfig set %s = %%s' % key
                value = change_conf[server][key] if change_conf[server].get(key) is not None else ''
                stdio.verbose('execute sql: %s' % (sql % value))
                cursor[server].execute(sql, [value])
                success_conf[key].append(server)
            except:
                global_ret = False
                stdio.exception('execute sql exception: %s' % (sql % value))
    for key in success_conf:
        if global_change_conf[key] == servers_num == len(success_conf):
            cluster_config.update_global_conf(key, value, False)
        for server in success_conf[key]:
            value = change_conf[server][key]
            cluster_config.update_server_conf(server,key, value, False)
    return plugin_context.return_true() if global_ret else None
