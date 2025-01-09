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

import time

from _deploy import InnerConfigItem


def bootstrap(plugin_context, *args, **kwargs):
    need_bootstrap = plugin_context.get_variable('need_bootstrap')
    if not need_bootstrap:
        return plugin_context.return_true()
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('cursor')
    added_components = cluster_config.get_deploy_added_components()
    global_conf = cluster_config.get_global_conf()
    changed_components = cluster_config.get_deploy_changed_components()
    be_depend = cluster_config.be_depends
    bootstrap = []
    floor_servers = {}
    zones_config = {}
    inner_config = {
        InnerConfigItem('$_zone_idc'): 'idc'
    }

    def is_bootstrap():
        sql = "select column_value from oceanbase.__all_core_table where table_name = '__all_global_stat' and column_name = 'baseline_schema_version'"
        ret = cursor.fetchone(sql, raise_exception=False, exc_level='verbose')
        if ret is False:
            return False
        return int(ret.get("column_value")) > 0

    if added_components:
        stdio.verbose('bootstrap for components: %s' % added_components)

    raise_cursor = cursor.raise_cursor
    if cluster_config.name in added_components:
        for server in cluster_config.servers:
            server_config = cluster_config.get_server_conf(server)
            zone = server_config['zone']
            if zone in floor_servers:
                floor_servers[zone].append('%s:%s' % (server.ip, server_config['rpc_port']))
            else:
                floor_servers[zone] = []
                zones_config[zone] = {}
                bootstrap.append('REGION "sys_region" ZONE "%s" SERVER "%s:%s"' % (server_config['zone'], server.ip, server_config['rpc_port']))

            zone_config = zones_config[zone]
            for key in server_config:
                if not isinstance(key, InnerConfigItem):
                    continue
                if key not in inner_config:
                    continue
                if key in zone_config:
                    continue
                zone_config[key] = server_config[key]
        try:
            sql = 'set session ob_query_timeout=1000000000'
            stdio.verbose('execute sql: %s' % sql)
            raise_cursor.execute(sql)
            sql = 'alter system bootstrap %s' % (','.join(bootstrap))
            stdio.start_loading('Cluster bootstrap')
            raise_cursor.execute(sql, exc_level='verbose')
            for zone in floor_servers:
                for addr in floor_servers[zone]:
                    sql = 'alter system add server "%s" zone "%s"' % (addr, zone)
                    raise_cursor.execute(sql)
            for zone in zones_config:
                zone_config = zones_config[zone]
                for key in zone_config:
                    sql = 'alter system modify zone %s set %s = %%s' % (zone, inner_config[key])
                    raise_cursor.execute(sql, [zone_config[key]])

            if global_conf.get('root_password') is not None:
                sql = 'alter user "root" IDENTIFIED BY %s'
                raise_cursor.execute(sql, [global_conf.get('root_password')])
                cursor.password = global_conf.get('root_password')
            stdio.stop_loading('succeed')
        except:
            if not is_bootstrap():
                stdio.stop_loading('fail')
                return plugin_context.return_false()
            stdio.stop_loading('succeed')

    # wait for server online
    all_server_online = False
    while not all_server_online:
        servers = cursor.fetchall('select * from oceanbase.__all_server', raise_exception=False, exc_level='verbose')
        if servers and all([s.get('status') for s in servers]):
            all_server_online = True
        else:
            time.sleep(1)

    return plugin_context.return_true()
