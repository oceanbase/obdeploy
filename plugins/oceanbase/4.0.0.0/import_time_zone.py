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

import os
import time

import const
from tool import Exector, COMMAND_ENV
from collections import defaultdict
from _stdio import FormatText


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
            tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, mode=mode, password=password, ip=tenant_ip, port=tenant_port, print_exception=print_exception)
            if tenant_cursor:
                if tenant not in tenant_cursor_cache[cursor]:
                    tenant_cursor_cache[cursor][tenant] = {}
                tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                break
    if not tenant_cursor and retries:
        time.sleep(1)
        return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, print_exception=print_exception, retries=retries-1, args=args, stdio=stdio)
    return tenant_cursor.execute(sql, args=args, raise_exception=False, exc_level='verbose', stdio=stdio) if tenant_cursor else False

def is_support_sdk_import_timezone(version):
    if (version >= '4.2.5.2' and version < '4.3.0.0') or version >= '4.3.5.2':
        return True
    return False

def import_time_zone(plugin_context, config_encrypted, create_tenant_options=[], cursor=None, scale_out_component='',  *args, **kwargs):
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
    if scale_out_component in const.COMPS_OCP + ['ocp-express']:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    if scale_out_component in ['obbinlog-ce']:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    cursors = []
    if plugin_context.get_variable('tenant_exists'):
        return plugin_context.return_true()
    no_password_cmd = ''
    for options in multi_options:
        global tenant_cursor
        tenant_cursor = None
        name = getattr(options, 'tenant_name', 'test')
        mode = getattr(options, 'mode', 'mysql')
        root_password = getattr(options, name+'_root_password', "") or ''
        if len(multi_options) == 1:
            plugin_context.set_variable('tenant_name', name)
            plugin_context.set_variable('root_password', root_password)
            plugin_context.set_variable('mode', mode)

        time_zone = getattr(options, 'time_zone', '')
        if not time_zone:
            time_zone = client.execute_command('date +%:z').stdout.strip()
        exec_sql_in_tenant(sql="SET GLOBAL time_zone='%s';" % time_zone, cursor=cursor, tenant=name, mode=mode, password=root_password if root_password else '')

        exector_path = getattr(options, 'exector_path', '/usr/obd/lib/executer')
        if tenant_cursor:
            exector = Exector(tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user, tenant_cursor.password, exector_path, stdio)
            for repository in repositories:
                if repository.name in const.COMPS_OB:
                    if is_support_sdk_import_timezone(repository.version):
                        sql = "ALTER SYSTEM LOAD MODULE DATA module = timezone tenant = '%s' infile = 'etc/'" % name
                        res = cursor.execute(sql, stdio=stdio)
                        if not res:
                            stdio.warn("execute timezone sql failed")
                        sql = "ALTER SYSTEM LOAD MODULE DATA module = gis tenant = '%s' infile = 'etc/';" % name
                        res = cursor.execute(sql, stdio=stdio)
                        if not res:
                            stdio.warn("execute gis sql failed")
                    else:
                        time_zone_info_param = os.path.join(repository.repository_dir, 'etc', 'timezone_V1.log')
                        srs_data_param = os.path.join(repository.repository_dir, 'etc', 'default_srs_data_mysql.sql')
                        if not exector.exec_script('import_time_zone_info.py', repository, param="-h {} -P {} -t {} -p '{}' -f {}".format(tenant_cursor.ip, tenant_cursor.port, name, global_config.get("root_password", ''), time_zone_info_param)):
                            stdio.warn('execute import_time_zone_info.py failed')
                        if not exector.exec_script('import_srs_data.py', repository, param="-h {} -P {} -t {} -p '{}' -f {}".format(tenant_cursor.ip, tenant_cursor.port, name, global_config.get("root_password", ''), srs_data_param)):
                            stdio.warn('execute import_srs_data.py failed')
                        break
            cursors.append(tenant_cursor)
            if mode == 'mysql':
                cmd_str = "obclient -h%s -P\'%s\' %s -u%s -Doceanbase -A\n"
                no_password_cmd = "obclient -h%s -P\'%s\' -u%s -Doceanbase -A\n"
            else:
                cmd_str = "obclient -h%s -P\'%s\' %s -u%s -A\n"
                no_password_cmd = "obclient -h%s -P\'%s\' -u%s -A\n"
            cmd_str = cmd_str % (tenant_cursor.ip, tenant_cursor.port, f"-p'{root_password}'" if not config_encrypted else '', tenant_cursor.user)
            no_password_cmd = no_password_cmd % (tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user)
            cmd = FormatText.success(cmd_str)
            stdio.print(cmd)
    return plugin_context.return_true(tenant_cursor=cursors, cmd=no_password_cmd)