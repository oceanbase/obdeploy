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


def drop_strong_sync_tenant(plugin_context, cursors, *args, **kwargs):
    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')

    stdio = plugin_context.stdio
    options = plugin_context.options

    deploy_name = plugin_context.cluster_config.deploy_name
    cursor = cursors.get(deploy_name)

    tenant_name = getattr(options, 'tenant_name', '')
    if not tenant_name:
        error('Please set tenant name')
        return
    elif tenant_name == 'sys':
        error('Prohibit deleting sys tenant')
        return

    tenant = None
    sql = "select * from oceanbase.DBA_OB_TENANTS where tenant_name = %s"
    tenant = cursor.fetchone(sql, [tenant_name])
    if tenant is False:
        return
    if not tenant:
        error('No such Tenant %s' % tenant_name)
        return

    try:
        primary_dict = plugin_context.cluster_config.get_component_attr('primary_tenant')
        if primary_dict and tenant_name in primary_dict:
            primary_info_list = primary_dict.get(tenant_name, [])
            if primary_info_list:
                p_deploy_name, p_tenant_name = primary_info_list[0]
                p_cursor = cursors.get(p_deploy_name)
                if p_cursor:
                    sql_mode = "SELECT PROTECTION_MODE, TENANT_ID FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
                    res_mode = p_cursor.fetchone(sql_mode, [p_tenant_name], raise_exception=False, exc_level='verbose')
                    if res_mode and 'PERFORMANCE' not in res_mode['PROTECTION_MODE'].upper():
                        sql_dest = "SELECT VALUE FROM oceanbase.CDB_OB_SYNC_STANDBY_DEST WHERE TENANT_ID = %s"
                        res_dest = p_cursor.fetchone(sql_dest, [res_mode['TENANT_ID']], raise_exception=False)
                        dest_value = res_dest['VALUE'] if res_dest else ''
                        if dest_value:
                            dest_parts = dict(p.split('=', 1) for p in dest_value.replace(',', ' ').split(' ') if '=' in p)
                            dest_user = dest_parts.get('USER', '')
                            dest_tenant = dest_user.split('@')[1] if '@' in dest_user else ''
                            if dest_tenant == tenant_name:
                                stdio.start_loading('Reset primary tenant %s sync mode' % tenant_name)
                                stdio.verbose('Downgrading primary tenant %s to MAXIMIZE PERFORMANCE' % p_tenant_name)
                                sql_downgrade = "ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE PERFORMANCE tenant = '%s'" % p_tenant_name
                                p_cursor.execute(sql_downgrade, raise_exception=True)
                                sql_clear = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % p_tenant_name
                                p_cursor.execute(sql_clear, raise_exception=True)
    except Exception as e:
        stdio.verbose('Downgrade primary tenant failed: %s' % e)
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
