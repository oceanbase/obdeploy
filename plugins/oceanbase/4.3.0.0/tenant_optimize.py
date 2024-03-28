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

import json
import os

from tool import FileUtil


def tenant_optimize(plugin_context, tenant_cursor=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    repositories = plugin_context.repositories
    tenant_cursor = plugin_context.get_return('create_tenant').get_return('tenant_cursor') if not tenant_cursor else tenant_cursor

    def _optimize(json_files):
        for file in json_files:
            if os.path.exists(file):
                with FileUtil.open(file, 'rb') as f:
                    data = json.load(f)
                    for _ in data:
                        if _['scenario'] == scenario:
                            if 'variables' in _:
                                for tenant_system_variable in _['variables']['tenant']:
                                    sql = f"SET GLOBAL {tenant_system_variable['name']} = {tenant_system_variable['value']};"
                                    for cursor in tenant_cursor:
                                        cursor.execute(sql)
                            if 'parameters' in _:
                                for tenant_default_parameter in _['parameters']['tenant']:
                                    sql = f"ALTER SYSTEM SET {tenant_default_parameter['name']} = '{tenant_default_parameter['value']}';"
                                    for cursor in tenant_cursor:
                                        cursor.execute(sql)
        return True

    if not tenant_cursor:
        stdio.error('tenant cursor is None')
        return plugin_context.return_false()

    path = ''
    for repository in repositories:
        if repository.name == cluster_config.name:
            path = repository.repository_dir
            break

    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        scenario = server_config['scenario']
        system_variable_json = f'{path}/etc/default_system_variable.json'
        default_parameters_json = f'{path}/etc/default_parameter.json'

        stdio.start_loading(f'optimize tenant with scenario: {scenario}')
        if _optimize([system_variable_json, default_parameters_json]):
            stdio.stop_loading('succeed')
            return plugin_context.return_true()
