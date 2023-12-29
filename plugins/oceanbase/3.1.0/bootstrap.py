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

from _deploy import InnerConfigItem


def bootstrap(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    cursor = plugin_context.get_return('connect').get_return('cursor')
    added_components = cluster_config.get_deploy_added_components()
    be_depend = cluster_config.be_depends
    stdio = plugin_context.stdio
    bootstrap = []
    floor_servers = {}
    zones_config = {}
    inner_config = {
        InnerConfigItem('$_zone_idc'): 'idc'
    }
    has_obproxy = False
    for componet_name in ['obproxy', 'obproxy-ce']:
        if componet_name in added_components and componet_name in be_depend:
            has_obproxy = True
            break
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
        raise_cursor = cursor.raise_cursor
        sql = 'set session ob_query_timeout=1000000000'
        raise_cursor.execute(sql)
        sql = 'alter system bootstrap %s' % (','.join(bootstrap))
        stdio.start_loading('Cluster bootstrap')
        raise_cursor.execute(sql, exc_level='verbose')
        for zone in floor_servers:
            for addr in floor_servers[zone]:
                sql = 'alter system add server "%s" zone "%s"' % (addr, zone)
                raise_cursor.execute(sql)
        global_conf = cluster_config.get_global_conf()
        if has_obproxy or 'proxyro_password' in global_conf:
            value = global_conf['proxyro_password'] if global_conf.get('proxyro_password') is not None else ''
            sql = 'create user "proxyro" IDENTIFIED BY %s'
            raise_cursor.execute(sql, [value])
            sql = 'grant select on oceanbase.* to proxyro IDENTIFIED BY %s'
            raise_cursor.execute(sql, [value])

        if global_conf.get('root_password') is not None:
            sql = 'alter user "root" IDENTIFIED BY %s'
            raise_cursor.execute(sql, [global_conf.get('root_password')])
        for zone in zones_config:
            zone_config = zones_config[zone]
            for key in zone_config:
                sql = 'alter system modify zone %s set %s = %%s' % (zone, inner_config[key])
                raise_cursor.execute(sql, [zone_config[key]])
        stdio.stop_loading('succeed')
    except:
        event = cursor.fetchall('select * from oceanbase.__all_rootservice_event_history where module = "bootstrap" and event = "bootstrap_succeed"')
        if not event:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    return plugin_context.return_true()
