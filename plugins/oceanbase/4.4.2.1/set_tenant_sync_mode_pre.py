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

from const import MAX_AVAILABILITY, MAX_PROTECTION

def set_tenant_sync_mode_pre(plugin_context, cursors=None, create_tenant_options=[], standbyro_password='', *args, **kwargs):
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    primary_deploy_name = cmds[1]
    primary_tenant = cmds[2]
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]

    primary_cursor = cursors.get(primary_deploy_name)
    if not primary_cursor:
        stdio.error('Missing cursor for primary.')
        return plugin_context.return_false()
    
    for options in multi_options:
        sync_mode = getattr(options, 'sync_mode', 'performance').strip().lower()
        net_timeout = getattr(options, 'net_timeout')
        health_check_time = getattr(options, 'health_check_time')
        if sync_mode != 'availability' and (net_timeout is not None or health_check_time is not None):
            stdio.warn("The parameters --net-timeout and --health-check-time only take effect when --sync-mode=availability.")
        elif sync_mode == 'availability':
            if net_timeout is not None and (net_timeout < 10 or net_timeout > 1200):
                stdio.error("The parameter net_timeout must be between [10, 1200]. Please provide a valid value.")
                return plugin_context.return_false()
            if health_check_time is not None and health_check_time < 0:
                stdio.error("The parameter health_check_time must be greater than 0. Please provide a valid value.")
                return plugin_context.return_false()

        if sync_mode in ['availability', 'protection']:
            sql_role = "SELECT TENANT_ROLE FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
            res_role = primary_cursor.fetchone(sql_role, (primary_tenant,), raise_exception=False)
            if not res_role:
                stdio.error("Primary tenant %s not found in %s" % (primary_tenant, primary_deploy_name))
                return plugin_context.return_false()
            
            if res_role['TENANT_ROLE'] != 'PRIMARY':
                stdio.error("Upstream tenant %s in %s is not PRIMARY (current role: %s). Cascading standby configuration is not supported for setting sync mode to %s." % (primary_tenant, primary_deploy_name, res_role['TENANT_ROLE'], sync_mode))
                return plugin_context.return_false()

            sql = "SELECT PROTECTION_MODE FROM oceanbase.DBA_OB_TENANTS WHERE tenant_name = %s"
            res = primary_cursor.fetchone(sql, (primary_tenant,))
            protection_mode = res.get('PROTECTION_MODE')
            if protection_mode in [MAX_AVAILABILITY, MAX_PROTECTION]:
                stdio.error(
                    'Primary tenant "%s" is already in sync mode: %s. '
                    'Cannot proceed with updating sync configuration in this state.'
                    % (primary_tenant, protection_mode)
                )
                return plugin_context.return_false()
    
    return plugin_context.return_true()