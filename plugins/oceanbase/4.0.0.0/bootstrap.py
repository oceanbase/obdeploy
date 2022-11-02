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

import sys
import time

if sys.version_info.major == 2:
    from MySQLdb import DatabaseError
else:
    from pymysql.err import DatabaseError

from _deploy import InnerConfigItem


def bootstrap(plugin_context, cursor, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    bootstrap = []
    floor_servers = {}
    zones_config = {}
    inner_config = {
        InnerConfigItem('$_zone_idc'): 'idc'
    }

    def is_bootstrap():
        sql = "select column_value from oceanbase.__all_core_table where table_name = '__all_global_stat' and column_name = 'baseline_schema_version'"
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
        return int(cursor.fetchone().get("column_value")) > 0

    try:
        if is_bootstrap():
            return plugin_context.return_true()
    except DatabaseError as e:
        stdio.verbose('%s:%s' % e.args)
    except:
        stdio.exception("")

    has_obproxy = False
    for componet_name in ['obproxy', 'obproxy-ce']:
        if componet_name in plugin_context.components:
            has_obproxy = True
            break
    inner_keys = inner_config.keys()
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
        sql = 'alter system bootstrap %s' % (','.join(bootstrap))
        stdio.start_loading('Cluster bootstrap')
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
        for zone in floor_servers:
            for addr in floor_servers[zone]:
                sql = 'alter system add server "%s" zone "%s"' % (addr, zone)
                stdio.verbose('execute sql: %s' % sql)
                cursor.execute(sql)
        global_conf = cluster_config.get_global_conf()
        if has_obproxy or 'proxyro_password' in global_conf:
            value = global_conf['proxyro_password'] if global_conf.get('proxyro_password') is not None else ''
            sql = 'create user "proxyro" IDENTIFIED BY %s'
            stdio.verbose(sql)
            cursor.execute(sql, [value])
            sql = 'grant select on oceanbase.* to proxyro IDENTIFIED BY %s'
            stdio.verbose(sql)
            cursor.execute(sql, [value])
        if global_conf.get('root_password') is not None:
            sql = 'alter user "root" IDENTIFIED BY "%s"' % global_conf.get('root_password')
            stdio.verbose('execute sql: %s' % sql)
            cursor.execute(sql)
        for zone in zones_config:
            zone_config = zones_config[zone]
            for key in zone_config:
                sql = 'alter system modify zone %s set %s = %%s' % (zone, inner_config[key])
                stdio.verbose('execute sql: %s' % sql)
                cursor.execute(sql, [zone_config[key]])
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    except:
        stdio.exception('')
        try:
            sql = 'set session ob_query_timeout=1000000000'
            stdio.verbose('execute sql: %s' % sql)
            cursor.execute(sql)
            if is_bootstrap():
                stdio.stop_loading('succeed')
                return plugin_context.return_true()
        except:
            stdio.exception('')
        stdio.stop_loading('fail')
        return plugin_context.return_false()
