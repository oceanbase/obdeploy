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

from const import MAX_PERFORMANCE, MAX_PROTECTION, MAX_AVAILABILITY

def _get_tenant_unit_service_list(cursor, tenant_name, stdio):
    query_sql = 'select group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)'
    res = cursor.fetchone(query_sql, (tenant_name,), raise_exception=False, exc_level='verbose')
    if not res or not res['ip_list']:
        return None
    return res['ip_list']


def _get_protection_mode(cursor, tenant_name, stdio):
    """Query PROTECTION_MODE for tenant from DBA_OB_TENANTS (sys tenant view).
    Returns protection_mode string or None if not found.
    """
    query_sql = (
        "SELECT PROTECTION_MODE FROM oceanbase.DBA_OB_TENANTS WHERE tenant_name = %s"
    )
    row = cursor.fetchone(query_sql, (tenant_name,), raise_exception=False, exc_level='verbose')
    return row.get('PROTECTION_MODE') or row.get('protection_mode')

def set_sync_mode(plugin_context, cursors=None, cluster_configs=None, *args, **kwargs):
    """
    Set primary-standby sync mode when OceanBase >= 4.4.2.1 and --sync-mode is availability or protection.
    - performance: no change, return True.
    - availability / protection: check primary PROTECTION_MODE; if already MAXIMIZE PROTECTION/AVAILABILITY then error;
      else set SYNC_STANDBY_DEST on both sides, set STANDBY TENANT TO MAXIMIZE PROTECTION/AVAILABILITY, then verify.
    """
    stdio = plugin_context.stdio
    options = plugin_context.options
    cmds = plugin_context.cmds

    sync_mode = (getattr(options, 'sync_mode', None) or 'performance').strip().lower()

    if sync_mode not in ('performance', 'availability', 'protection'):
        stdio.error('Invalid --mode: %s. Supported: performance, availability, protection.' % sync_mode)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    cursors = cursors or plugin_context.get_variable('cursors') or {}
    
    standby_deploy_name = cmds[0]
    standby_tenant_name = cmds[1]
    
    # These should be set by set_sync_mode_pre
    primary_deploy_name = plugin_context.get_variable('primary_deploy_name')
    primary_tenant_name = plugin_context.get_variable('primary_tenant_name')
    
    if not primary_deploy_name:
        # Fallback if pre-check didn't run or failed silently (shouldn't happen)
        stdio.error('Primary cluster info missing. Ensure set_sync_mode_pre ran successfully.')
        return plugin_context.return_false()

    primary_cursor = cursors.get(primary_deploy_name)
    standby_cursor = cursors.get(standby_deploy_name)
    
    if not primary_cursor or not standby_cursor:
        stdio.error('Missing cursor for primary or standby deploy.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # Get passwords
    # Try to get standbyro password from options or config
    standbyro_password = getattr(options, 'standbyro_password', None)
    if not standbyro_password:
        # Try to get from primary config
        p_config = cluster_configs.get(primary_deploy_name)
        if p_config:
            pw_dict = p_config.get_component_attr('standbyro_password')
            if pw_dict:
                standbyro_password = pw_dict.get(primary_tenant_name)
    
    if not standbyro_password:
        stdio.error('Missing standbyro password. Use --standbyro-password option.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.start_loading('Set tenant sync mode to %s' % sync_mode)
    
    if sync_mode == 'performance':
        # Downgrade logic
        # 1. Set MAXIMIZE PERFORMANCE
        set_mode_sql = "ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE PERFORMANCE tenant = '%s'" % primary_tenant_name
        if not primary_cursor.execute(set_mode_sql, raise_exception=False, exc_level='verbose'):
            stdio.error('Primary set STANDBY TENANT TO MAXIMIZE PERFORMANCE failed.')
            stdio.stop_loading('fail')
            return plugin_context.return_false()
            
        # Verify downgrade
        max_wait = 120
        step = 5
        downgraded = False
        for _ in range(0, max_wait, step):
            pm_pri = _get_protection_mode(primary_cursor, primary_tenant_name, stdio)
            pm_sta = _get_protection_mode(standby_cursor, standby_tenant_name, stdio)
            if pm_pri and pm_sta:
                if MAX_PERFORMANCE == pm_pri and MAX_PERFORMANCE == pm_sta:
                    downgraded = True
                    break
            time.sleep(step)
        
        if not downgraded:
            stdio.error('Verification timeout: Failed to downgrade to MAXIMIZE PERFORMANCE.')
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        # 2. Reset SYNC_STANDBY_DEST on Primary
        reset_sql_pri = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % primary_tenant_name
        if not primary_cursor.execute(reset_sql_pri, raise_exception=False, exc_level='verbose'):
            stdio.warn('Primary reset SYNC_STANDBY_DEST failed. Please check manually.')

        # 3. Reset SYNC_STANDBY_DEST on Standby
        reset_sql_stby = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % standby_tenant_name
        if not standby_cursor.execute(reset_sql_stby, raise_exception=False, exc_level='verbose'):
            stdio.warn('Standby reset SYNC_STANDBY_DEST failed. Please check manually.')
            
        stdio.stop_loading('succeed')
        return plugin_context.return_true()

    # Upgrade Logic (Availability / Protection)

    # Build SERVICE= list for standby (used when setting dest on primary) and for primary (used when setting dest on standby)
    standby_service = _get_tenant_unit_service_list(standby_cursor, standby_tenant_name, stdio)
    primary_service = _get_tenant_unit_service_list(primary_cursor, primary_tenant_name, stdio)
    
    if not standby_service:
        stdio.error('Failed to get standby tenant %s:%s unit list.' % (standby_deploy_name, standby_tenant_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    if not primary_service:
        stdio.error('Failed to get primary tenant %s:%s unit list.' % (primary_deploy_name, primary_tenant_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # Escape password for use inside double-quoted string (escape backslash and double-quote)
    pwd_escaped = (standbyro_password or '').replace('\\', '\\\\').replace('"', '\\"')
    dest_user = 'standbyro@%s' % standby_tenant_name
    dest_user_primary = 'standbyro@%s' % primary_tenant_name

    if sync_mode == 'protection':
        # MAXIMIZE PROTECTION
        dest_primary = 'SERVICE=%s USER=%s PASSWORD=%s' % (standby_service, dest_user, pwd_escaped)
        dest_standby = 'SERVICE=%s USER=%s PASSWORD=%s' % (primary_service, dest_user_primary, pwd_escaped)
        set_mode_sql = "ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE PROTECTION tenant ='%s'" % primary_tenant_name
        expected_mode = MAX_PROTECTION
        expected_level = MAX_PROTECTION
    else:
        # availability -> MAXIMIZE AVAILABILITY (optional NET_TIMEOUT / HEALTH_CHECK_TIME)
        net_timeout = getattr(options, 'net_timeout', None)
        health_check_time = getattr(options, 'health_check_time', None)
        service_options = ''
        if net_timeout:
            service_options += ' NET_TIMEOUT=%s' % net_timeout
        if health_check_time:
            service_options += ' HEALTH_CHECK_TIME=%s' % health_check_time
        dest_primary = 'SERVICE=%s%s USER=%s PASSWORD=%s' % (standby_service, service_options, dest_user, pwd_escaped)
        dest_standby = 'SERVICE=%s%s USER=%s PASSWORD=%s' % (primary_service, service_options, dest_user_primary, pwd_escaped)
        set_mode_sql = "ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE AVAILABILITY tenant = '%s'" % primary_tenant_name
        expected_mode = MAX_AVAILABILITY
        expected_level = MAX_AVAILABILITY

    # 1. Primary: set sync standby dest to standby
    sql_primary_dest = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '%s' tenant = '%s'" % (dest_primary, primary_tenant_name)
    stdio.verbose('Primary set SYNC_STANDBY_DEST: %s' % sql_primary_dest)
    if not primary_cursor.execute(sql_primary_dest, raise_exception=False, exc_level='verbose'):
        stdio.error('Primary set SYNC_STANDBY_DEST failed.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # 2. Standby: set sync standby dest to primary
    sql_standby_dest = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '%s' tenant = '%s'" % (dest_standby, standby_tenant_name)
    stdio.verbose('Standby set SYNC_STANDBY_DEST: %s' % sql_standby_dest)
    if not standby_cursor.execute(sql_standby_dest, raise_exception=False, exc_level='verbose'):
        stdio.error('Standby set SYNC_STANDBY_DEST failed.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # 3. Primary: set standby tenant to MAXIMIZE PROTECTION / MAXIMIZE AVAILABILITY
    if not primary_cursor.execute(set_mode_sql, raise_exception=False, exc_level='verbose'):
        stdio.error('Primary set STANDBY TENANT TO %s failed.' % expected_mode)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # 4. Wait and verify: both primary and standby show expected PROTECTION_MODE and PROTECTION_LEVEL
    max_wait = 120
    step = 5
    for _ in range(0, max_wait, step):
        pm_pri = _get_protection_mode(primary_cursor, primary_tenant_name, stdio)
        pm_sta = _get_protection_mode(standby_cursor, standby_tenant_name, stdio)
        if pm_pri and pm_sta:
            if expected_mode == pm_pri and expected_mode == pm_sta:
                stdio.stop_loading('succeed')
                stdio.verbose('Sync mode set and verified: %s / %s' % (expected_mode, expected_level))
                return plugin_context.return_true()
        time.sleep(step)
    stdio.stop_loading('fail')
    stdio.error(
        'Verification timeout: primary or standby PROTECTION_MODE/PROTECTION_LEVEL did not become %s.' % expected_mode
    )
    return plugin_context.return_false()
