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


def bootstrap(plugin_context, cursor, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    bootstrap = []
    floor_servers = {}
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        zone = server_config['zone']
        if zone in floor_servers:
            floor_servers[zone].append('%s:%s' % (server.ip, server_config['rpc_port']))
        else:
            floor_servers[zone] = []
            bootstrap.append('REGION "sys_region" ZONE "%s" SERVER "%s:%s"' % (server_config['zone'], server.ip, server_config['rpc_port']))
    try:
        sql = 'set session ob_query_timeout=1000000000'
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
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
        if 'proxyro_password' in global_conf or 'obproxy' in plugin_context.components:
            value = global_conf['proxyro_password'] if global_conf.get('proxyro_password') is not None else ''
            sql = 'create user "proxyro" IDENTIFIED BY "%s"' % value
            stdio.verbose(sql)
            cursor.execute(sql)
            sql = 'grant select on oceanbase.* to proxyro IDENTIFIED BY "%s"' % value
            stdio.verbose(sql)
            cursor.execute(sql)
        if global_conf.get('root_password'):
            sql = 'alter user "root" IDENTIFIED BY "%s"' % global_conf.get('root_password')
            stdio.verbose('execute sql: %s' % sql)
            cursor.execute(sql)
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    except:
        stdio.exception('')
        try:
            cursor.execute('select * from oceanbase.__all_rootservice_event_history where module = "bootstrap" and event = "bootstrap_succeed"')
            event = cursor.fetchall()
            if not event:
                raise Exception('Not found bootstrap_succeed event')
            stdio.stop_loading('succeed')
            plugin_context.return_true()
        except:
            stdio.stop_loading('fail')
            stdio.exception('')
            plugin_context.return_false()
