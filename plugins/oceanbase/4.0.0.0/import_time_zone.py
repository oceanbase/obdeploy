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

import os
import time

import const
from tool import Exector
from collections import defaultdict


tenant_cursor_cache = defaultdict(dict)


def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', print_exception=True, retries=20, args=[], stdio=None):
    global tenant_cursor
    if not user:
        user = 'SYS' if mode == 'oracle' else 'root'
    # find tenant ip, port
    tenant_cursor = None
    if cursor in tenant_cursor_cache and tenant in tenant_cursor_cache[cursor] and user in tenant_cursor_cache[cursor][tenant]:
        tenant_cursor = tenant_cursor_cache[cursor][tenant][user]
    else:
        query_sql = "select a.SVR_IP,c.SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
        tenant_server_ports = cursor.fetchall(query_sql, (tenant, ), raise_exception=False, exc_level='verbose')
        for tenant_server_port in tenant_server_ports:
            tenant_ip = tenant_server_port['SVR_IP']
            tenant_port = tenant_server_port['SQL_PORT']
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, print_exception=print_exception)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, print_exception=print_exception, retries=retries-1, args=args, stdio=stdio)
    return tenant_cursor.execute(sql, args=args, raise_exception=False, exc_level='verbose', stdio=stdio) if tenant_cursor else False


def import_time_zone(plugin_context, create_tenant_options=[], cursor=None, scale_out_component='',  *args, **kwargs):
    clients = plugin_context.clients
    repositories = plugin_context.repositories
    client = clients[plugin_context.cluster_config.servers[0]]
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_global_conf()
    if cluster_config.name not in const.COMPS_OB:
        if const.COMP_OB_CE in cluster_config.depends:
            global_config = cluster_config.get_depend_config(const.COMP_OB_CE)
        if const.COMP_OB in cluster_config.depends:
            global_config = cluster_config.get_depend_config(const.COMP_OB)
    stdio = plugin_context.stdio

    cursor = plugin_context.get_return('connect', spacename=cluster_config.name).get_return('cursor') if not cursor else cursor
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    if scale_out_component in const.COMPS_OCP_CE_AND_EXPRESS:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    cursors = []
    if plugin_context.get_variable('tenant_exists'):
        return plugin_context.return_true()
    for options in multi_options:
        global tenant_cursor
        tenant_cursor = None
        name = getattr(options, 'tenant_name', 'test')
        mode = getattr(options, 'mode', 'mysql')
        root_password = getattr(options, name+'_root_password', "")

        time_zone = getattr(options, 'time_zone', '')
        if not time_zone:
            time_zone = client.execute_command('date +%:z').stdout.strip()
        exec_sql_in_tenant(sql="SET GLOBAL time_zone='%s';" % time_zone, cursor=cursor, tenant=name, mode=mode, password=root_password if root_password else '')

        exector_path = getattr(options, 'exector_path', '/usr/obd/lib/executer')
        if tenant_cursor:
            exector = Exector(tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user, tenant_cursor.password, exector_path, stdio)
            for repository in repositories:
                if repository.name in const.COMPS_OB:
                    time_zone_info_param = os.path.join(repository.repository_dir, 'etc', 'timezone_V1.log')
                    srs_data_param = os.path.join(repository.repository_dir, 'etc', 'default_srs_data_mysql.sql')
                    if not exector.exec_script('import_time_zone_info.py', repository, param="-h {} -P {} -t {} -p '{}' -f {}".format(tenant_cursor.ip, tenant_cursor.port, name, global_config.get("root_password", ''), time_zone_info_param)):
                        stdio.warn('execute import_time_zone_info.py failed')
                    if not exector.exec_script('import_srs_data.py', repository, param="-h {} -P {} -t {} -p '{}' -f {}".format(tenant_cursor.ip, tenant_cursor.port, name, global_config.get("root_password", ''), srs_data_param)):
                        stdio.warn('execute import_srs_data.py failed')
                    break
            cursors.append(tenant_cursor)
            cmd = 'obclient -h%s -P%s -u%s -Doceanbase -A\n' % (tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user)
            stdio.print(cmd)
    return plugin_context.return_true(tenant_cursor=cursors)