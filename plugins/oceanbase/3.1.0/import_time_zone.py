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
from tool import Exector


tenant_cursor = None


def exec_sql_in_tenant(sql, cursor, tenant, mode, retries=10, args=[], stdio=None):
    global tenant_cursor
    if not tenant_cursor:
        user = 'SYS' if mode == 'oracle' else 'root'
        tenant_cursor = cursor.new_cursor(tenant=tenant, user=user)
        if not tenant_cursor and retries:
            retries -= 1
            time.sleep(2)
            return exec_sql_in_tenant(sql, cursor, tenant, mode, retries=retries, args=args, stdio=stdio)
    return tenant_cursor.execute(sql, args=args, stdio=stdio)


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

    if plugin_context.get_variable('tenant_exists'):
        return plugin_context.return_true()
    for options in multi_options:
        global tenant_cursor
        tenant_cursor = None
        name = getattr(options, 'tenant_name', 'test')
        mode = getattr(options, 'mode', 'mysql')
        time_zone = getattr(options, 'time_zone', '')

        if mode == 'oracle':
            stdio.verbose('Import time zone in oracle tenant is not supported')
            return plugin_context.return_true()

        if not time_zone:
            time_zone = client.execute_command('date +%:z').stdout.strip()
        exec_sql_in_tenant(sql="SET GLOBAL time_zone='%s';" % time_zone, cursor=cursor, tenant=name, mode=mode, stdio=stdio)

        exector_path = getattr(options, 'exector_path', '/usr/obd/lib/executer')
        if tenant_cursor:
            exector = Exector(tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user, tenant_cursor.password, exector_path, stdio)
            for repository in repositories:
                if repository.name in const.COMPS_OB:
                    time_zone_info_param = os.path.join(repository.repository_dir, 'etc', 'timezone_V1.log')
                    if not exector.exec_script('import_time_zone_info.py', repository, param="-h {} -P {} -t {} -p '{}' -f {}".format(tenant_cursor.ip, tenant_cursor.port, name, global_config.get("root_password", ''), time_zone_info_param)):
                        stdio.warn('execute import_time_zone_info.py failed')
                    break
            cmd = 'obclient -h%s -P%s -u%s -Doceanbase -A\n' % (tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user)
            stdio.print(cmd)
    return plugin_context.return_true()