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
    for server in servers:
        change_conf[server] = {}
        stdio.verbose('get %s old configuration' % (server))
        config = cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s new configuration' % (server))
        new_config = new_cluster_config.get_server_conf_with_default(server)
        stdio.verbose('get %s cluster address' % (server))
        cluster_server[server] = '%s:%s' % (server.ip, config['rpc_port'])
        stdio.verbose('compare configuration of %s' % (server))
        for key in new_config:
            n_value = new_config[key]
            if key not in config or config[key] != n_value:
                change_conf[server][key] = n_value
                if key not in global_change_conf:
                    global_change_conf[key] = {'value': n_value, 'count': 1}
                elif n_value == global_change_conf[key]['value']:
                    global_change_conf[key]['count'] += 1

    servers_num = len(servers)
    stdio.verbose('apply new configuration')
    for key in global_change_conf:
        msg = ''
        try:
            if key in ['proxyro_password', 'root_password']:
                if global_change_conf[key]['count'] != servers_num:
                    stdio.warn('Invalid: proxyro_password is not a single server configuration item')
                    continue
                value = change_conf[server][key] if change_conf[server].get(key) is not None else ''
                user = key.split('_')[0]
                msg = sql = 'CREATE USER IF NOT EXISTS %s IDENTIFIED BY "%s"' % (user, value)
                stdio.verbose('execute sql: %s' % sql)
                cursor.execute(sql)
                msg = sql = 'alter user "%s" IDENTIFIED BY "%s"' % (user, value)
                stdio.verbose('execute sql: %s' % sql)
                cursor.execute(sql)
                continue
            if global_change_conf[key]['count'] == servers_num:
                sql = 'alter system set %s = %%s' % key
                value = change_conf[server][key]
                msg = sql % value
                stdio.verbose('execute sql: %s' % msg)
                cursor.execute(sql, [value])
                cluster_config.update_global_conf(key, value, False)
                continue
            for server in servers:
                if key not in change_conf[server]:
                    continue
                sql = 'alter system set %s = %%s server=%%s' % key
                value = (change_conf[server][key], cluster_server[server])
                msg = sql % value
                stdio.verbose('execute sql: %s' % msg)
                cursor.execute(sql, value)
                cluster_config.update_server_conf(server,key, value, False)
        except:
            global_ret = False
            stdio.exception('execute sql exception: %s' % msg)

    cursor.execute('alter system reload server')
    cursor.execute('alter system reload zone')
    cursor.execute('alter system reload unit')
    return plugin_context.return_true() if global_ret else None
