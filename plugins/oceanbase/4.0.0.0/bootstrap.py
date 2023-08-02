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
from copy import deepcopy
from optparse import Values

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
        ret = cursor.fetchone(sql, raise_exception=False, exc_level='verbose')
        if ret is False:
            return False
        return int(ret.get("column_value")) > 0

    has_obproxy = False
    for componet_name in ['obproxy', 'obproxy-ce']:
        if componet_name in plugin_context.components:
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
        stdio.verbose('execute sql: %s' % sql)
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

        has_obagent = "obagent" in plugin_context.components
        if has_obagent or 'ocp_agent_monitor_password' in global_conf:
            value = global_conf['ocp_agent_monitor_password'] if global_conf.get('ocp_agent_monitor_password') is not None else ''
            sql = 'create user "ocp_monitor" IDENTIFIED BY %s'
            stdio.verbose(sql)
            raise_cursor.execute(sql, [value])
            sql = 'grant select on oceanbase.* to ocp_monitor IDENTIFIED BY %s'
            stdio.verbose(sql)
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
        if not is_bootstrap():
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    has_ocp = 'ocp-express' in plugin_context.components
    if any([key in global_conf for key in ["ocp_meta_tenant", "ocp_meta_db", "ocp_meta_username", "ocp_meta_password"]]):
        has_ocp = True
    if has_ocp:
        global_conf_with_default = deepcopy(cluster_config.get_global_conf_with_default())
        original_global_conf = cluster_config.get_original_global_conf()
        ocp_meta_tenant_prefix = 'ocp_meta_tenant_'
        for key in global_conf_with_default:
            if key.startswith(ocp_meta_tenant_prefix) and original_global_conf.get(key, None):
                global_conf_with_default['ocp_meta_tenant'][key.replace(ocp_meta_tenant_prefix, '', 1)] = global_conf_with_default[key]
        tenant_info = global_conf_with_default["ocp_meta_tenant"]
        tenant_info["variables"] = "ob_tcp_invited_nodes='%'"
        tenant_info["create_if_not_exists"] = True
        tenant_info["database"] = global_conf_with_default["ocp_meta_db"]
        tenant_info["db_username"] = global_conf_with_default["ocp_meta_username"]
        tenant_info["db_password"] = global_conf_with_default.get("ocp_meta_password", "")
        tenant_options = Values(tenant_info)
        plugin_context.set_variable("create_tenant_options", tenant_options)
    # wait for server online
    all_server_online = False
    while not all_server_online:
        servers = cursor.fetchall('select * from oceanbase.__all_server', raise_exception=False, exc_level='verbose')
        if servers and all([s.get('status') for s in servers]):
            all_server_online = True
        else:
            time.sleep(1)

    return plugin_context.return_true()
