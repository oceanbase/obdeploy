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

def standby_status_check(plugin_context, cluster_configs, cursors={}, *args, **kwargs):
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    standby_cluster_name = cmds[0]
    standby_tenant_name = cmds[1]

    standby_cursor = cursors.get(standby_cluster_name)
    if not standby_cursor:
        stdio.error(f"Get {standby_cluster_name} is failed.")
        return
    
    sql = 'SELECT TENANT_ID,TENANT_ROLE FROM oceanbase.DBA_OB_TENANTS where tenant_name=%s'
    res = standby_cursor.fetchone(sql, (standby_tenant_name, ))
    if not res:
        stdio.error('Query {}:{} tenant fail.'.format(standby_cluster_name, standby_tenant_name))
        return

    if not res['TENANT_ID']:
        stdio.error('Query {}:{} tenant_id fail.'.format(standby_cluster_name, standby_tenant_name))
        return

    if res['TENANT_ROLE'] != "STANDBY":
        stdio.error("The standby tenant has not been restored yet. Please try again later.")
        return
    
    sql = 'SELECT SYNC_STATUS FROM oceanbase.v$ob_ls_log_restore_status WHERE TENANT_ID=%s' % res['TENANT_ID']
    res = standby_cursor.fetchone(sql)
    if not res:
        stdio.error("The standby tenant {}:{} find log restore status is failed. Please try again later.".format(standby_cluster_name, standby_tenant_name))
        return
    if res['SYNC_STATUS'] != 'NORMAL':
        stdio.error("The standby tenant {}:{} abnormal synchronization in progress. Please try again later.".format(standby_cluster_name, standby_tenant_name))
        return
    
    cluster_config = cluster_configs.get(standby_cluster_name)
    if not cluster_configs:
        stdio.error("Get {} cluster config is failed.".format(standby_cluster_name))
        return
    primary_dict = cluster_config.get_component_attr('primary_tenant')
    if not primary_dict:
        stdio.error('The primary_tenant data is empty in inner_config')
        return
    primary_info = primary_dict[standby_tenant_name]
    if not primary_info:
        stdio.error('Tenant {} cannot find the primary tenant information'.format(standby_tenant_name))
        return
    primary_deploy = primary_info[0][0]
    primary_tenant = primary_info[0][1]
    
    primary_cursor = plugin_context.get_variable('cursors').get(primary_deploy)
    if not primary_cursor:
        stdio.error(f"Get {primary_deploy} is failed. Please check the primary_cluster information")
        return
    sql = 'select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME=%s'
    primary_tenant_info = primary_cursor.fetchone(sql, (primary_tenant, ))
    if not primary_tenant_info:
        stdio.error('Primary tenant {}:{} is not exist. please check the primary_tenant information'.format(primary_deploy, primary_tenant))
        return
    plugin_context.set_variable('primary_deploy', primary_deploy)
    plugin_context.set_variable('primary_tenant', primary_tenant)

    return plugin_context.return_true()