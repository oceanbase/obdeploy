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

from tool import get_option

def restore_standby_tenant(plugin_context, cursors={}, *args, **kwargs):
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    stdio = plugin_context.stdio
    options = plugin_context.options
    cmds = plugin_context.cmds
    primary_tenant = cmds[2]
    name = get_option(options, 'tenant_name', primary_tenant)
    standby_cursor = cursors.get(standby_deploy_name)
    error = plugin_context.get_variable('error')

    data_backup_uri = plugin_context.get_variable('data_backup_uri')
    archive_log_uri = plugin_context.get_variable('archive_log_uri')
    uri = f"{data_backup_uri},{archive_log_uri}"

    pool_name = plugin_context.get_variable(name).get('pool_name')
    restore_option = f'pool_list={pool_name}'
    locality = get_option(options, 'locality', '')
    if locality:
        restore_option += f'&locality={locality}'
    primary_zone = get_option(options, 'primary_zone', 'RANDOM')
    restore_option += f'&primary_zone={primary_zone}'

    decrption = get_option(options, 'decryption', '')
    if decrption:
        sql = "SET DECRYPTION IDENTIFIED BY '%s'" % decrption
        primary_cluster = cmds[1]
        primary_cursor = cursors.get(primary_cluster)
        res = primary_cursor.execute(sql, stdio=stdio)
        if not res:
            error(f"Failed to set {primary_cluster} decryption")
            return
        
    stdio.start_loading('Restoring the standby tenant is in progress')    
    sql = f"ALTER SYSTEM RESTORE {name} FROM '{uri}' WITH '{restore_option}'"
    try:
        standby_cursor.execute(sql, raise_exception=True, exc_level='verbose', stdio=stdio)
    except Exception as e:
        stdio.error(f"Failed to restore the {name} standby tenant: {e}")
        stdio.stop_loading('failed')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    setattr(plugin_context.options, 'tenant', name)
    return plugin_context.return_true()
