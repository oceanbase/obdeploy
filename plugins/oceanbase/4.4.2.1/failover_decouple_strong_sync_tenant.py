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

import time
from const import MAX_PERFORMANCE


def _get_protection_mode(cursor, tenant_name, stdio):
    sql = "SELECT PROTECTION_MODE FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
    try:
        res = cursor.fetchone(sql, [tenant_name], raise_exception=False, exc_level='verbose')
        if res:
            return res['PROTECTION_MODE'].upper()
    except Exception as e:
        stdio.verbose('Get protection mode failed: %s' % e)
    return None


def failover_decouple_strong_sync_tenant(plugin_context, cursors={}, *args, **kwargs):
    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')

    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    
    option_type = cmds[2]

    standby_deploy_name = plugin_context.cluster_config.deploy_name
    standby_cursor = cursors.get(standby_deploy_name)
    standby_tenant_name = cmds[1]

    if not standby_tenant_name:
        error('Please set tenant name')
        return

    if not standby_cursor:
        error("Connect to %s failed." % standby_deploy_name)
        return

    stdio.start_loading('Check and downgrade sync mode for %s %s' % (option_type, standby_tenant_name))

    try:
        if option_type == 'failover':
            sql_mode = "SELECT PROTECTION_MODE FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_NAME = %s"
            res_mode = standby_cursor.fetchone(sql_mode, [standby_tenant_name], raise_exception=False, exc_level='verbose')
            if res_mode:
                stdio.verbose("Tenant %s current protection mode is %s, executing clear SYNC_STANDBY_DEST" % (standby_tenant_name, res_mode['PROTECTION_MODE']))
                sql_clear = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % standby_tenant_name
                standby_cursor.execute(sql_clear, raise_exception=True)
                
        elif option_type == 'decouple':
            pm_sta = _get_protection_mode(standby_cursor, standby_tenant_name, stdio)
            if pm_sta and 'PERFORMANCE' not in pm_sta:
                primary_dict = plugin_context.cluster_config.get_component_attr('primary_tenant')
                if primary_dict and standby_tenant_name in primary_dict:
                    primary_info_list = primary_dict.get(standby_tenant_name, [])
                    if primary_info_list:
                        primary_deploy_name, primary_tenant_name = primary_info_list[0]
                        primary_cursor = cursors.get(primary_deploy_name)
                        
                        if primary_cursor:
                            stdio.verbose('Downgrading primary tenant %s to MAXIMIZE PERFORMANCE' % primary_tenant_name)
                            set_mode_sql = "ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE PERFORMANCE tenant = '%s'" % primary_tenant_name
                            if not primary_cursor.execute(set_mode_sql, raise_exception=False, exc_level='verbose'):
                                stdio.error('Primary set STANDBY TENANT TO MAXIMIZE PERFORMANCE failed.')
                                return plugin_context.return_false()
                            else:
                                # Verify downgrade
                                max_wait = 120
                                step = 5
                                downgraded = False
                                for _ in range(0, max_wait, step):
                                    pm_pri = _get_protection_mode(primary_cursor, primary_tenant_name, stdio)
                                    pm_sta_cur = _get_protection_mode(standby_cursor, standby_tenant_name, stdio)
                                    if pm_pri and pm_sta_cur:
                                        if MAX_PERFORMANCE in pm_pri and MAX_PERFORMANCE in pm_sta_cur:
                                            downgraded = True
                                            break
                                    time.sleep(step)
                                
                                if not downgraded:
                                    stdio.warn('Verification timeout: Failed to downgrade to MAXIMIZE PERFORMANCE.')
                            
                            # Reset SYNC_STANDBY_DEST on Primary
                            reset_sql_pri = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % primary_tenant_name
                            if not primary_cursor.execute(reset_sql_pri, raise_exception=False, exc_level='verbose'):
                                stdio.error('Primary reset SYNC_STANDBY_DEST failed. Please check manually.')
                                return plugin_context.return_false()

                # Reset SYNC_STANDBY_DEST on Standby
                reset_sql_stby = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % standby_tenant_name
                if not standby_cursor.execute(reset_sql_stby, raise_exception=False, exc_level='verbose'):
                    stdio.error('Standby reset SYNC_STANDBY_DEST failed. Please check manually.')
                    return plugin_context.return_false()

    except Exception as e:
        stdio.verbose("Downgrade strong sync failed: %s" % e)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
