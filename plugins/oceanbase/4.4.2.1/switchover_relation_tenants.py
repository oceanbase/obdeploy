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

from collections import defaultdict
import time
from const import SERVICE_MODE

tenant_cursor_cache = defaultdict(dict)

def switchover_relation_tenants(plugin_context, cluster_configs, cursors={}, *args, **kwargs):
    def switchover_service_standby(deploy_name, tenant_name, primary_cluster, primary_tenant, mode='mysql'):
        p_config = cluster_configs.get(primary_cluster)
        standbyro_password = ''
        if p_config:
            pw_dict = p_config.get_component_attr('standbyro_password')
            if pw_dict:
                standbyro_password = pw_dict.get(primary_tenant, '')
        
        if not standbyro_password:
            standbyro_password = getattr(plugin_context.options, 'standbyro_password', '')
            
        sql = 'ALTER SYSTEM SET LOG_RESTORE_SOURCE = "SERVICE={} USER=standbyro@{} PASSWORD={}"'.format(ip_list, primary_tenant, standbyro_password)
        try:
            exec_sql_in_tenant(sql, cursors.get(deploy_name), tenant_name, mode, password=standby_tenant_password, raise_exception=True, retries=5)
        except Exception as e:
            retry_message = 'After resolving the issue, you can retry by manually executing SQL:\'{}\' with the root user in the tenant {}:{}.'.format(sql, deploy_name, tenant_name)
            stdio.exception("Set the old primary`s standby tenant {}:{} as a standby tenant of the new primary`s standby tenant {}:{} failed:{}. \n {}".format(deploy_name, tenant_name, deploy_name, primary_tenant, e, retry_message))
            return False

        return True

    def switchover_location_standby(deploy_name, tenant_name, archive_path):
        deploy_cursor = cursors.get(deploy_name)
        sql = "ALTER SYSTEM SET LOG_RESTORE_SOURCE ='LOCATION=%s' TENANT = %s" % (archive_path, tenant_name)
        if deploy_cursor.execute(sql, raise_exception=True, stdio=stdio) is False:
            error()
            return
        return True

    def get_ip_list(cursor, deploy_name, tenant, stdio):
        if not cursor:
            stdio.verbose('Get ip list error: failed to connect {}.'.format(deploy_name))
            return
        res = cursor.fetchone('select TENANT_ID, group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host,TENANT_ID from oceanbase.cdb_ob_access_point where tenant_name=%s)', (tenant,), raise_exception=False)
        if not res:
            stdio.error('{}:{} not exist.'.format(deploy_name, tenant))
            return
        return res['ip_list']

    def exec_sql_in_tenant(sql, cursor, tenant, mode, user='', password='', raise_exception=False, retries=20):
        if not user:
            user = 'SYS' if mode == 'oracle' else 'root'
        # find tenant ip, port
        tenant_cursor = None
        if cursor in tenant_cursor_cache and tenant in tenant_cursor_cache[cursor] and user in tenant_cursor_cache[cursor][tenant]:
            tenant_cursor = tenant_cursor_cache[cursor][tenant][user]
        else:
            query_sql = "select a.SVR_IP as SVR_IP, c.SQL_PORT as SQL_PORT from oceanbase.DBA_OB_UNITS as a, oceanbase.DBA_OB_TENANTS as b, oceanbase.DBA_OB_SERVERS as c  where a.TENANT_ID=b.TENANT_ID and a.SVR_IP=c.SVR_IP and a.svr_port=c.SVR_PORT and TENANT_NAME=%s"
            tenant_server_ports = cursor.fetchall(query_sql, (tenant,), raise_exception=False, exc_level='verbose')
            for tenant_server_port in tenant_server_ports:
                tenant_ip = tenant_server_port['SVR_IP']
                tenant_port = tenant_server_port['SQL_PORT']
                tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, mode=mode, print_exception=raise_exception)
                if tenant_cursor:
                    if tenant not in tenant_cursor_cache[cursor]:
                        tenant_cursor_cache[cursor][tenant] = {}
                    tenant_cursor_cache[cursor][tenant][user] = tenant_cursor
                    break
        if not tenant_cursor and retries:
            time.sleep(1)
            return exec_sql_in_tenant(sql, cursor, tenant, mode, user, password, raise_exception=raise_exception, retries=retries - 1)
        return tenant_cursor.execute(sql, raise_exception=False, exc_level='verbose') if tenant_cursor else False

    def error(msg='', *arg, **kwargs):
        msg and stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('failed')

    def call_plugin(plugin, *args, **kwargs):
        return plugin(plugin_context.namespace, plugin_context.namespaces, plugin_context.deploy_name, plugin_context.deploy_status,
                      plugin_context.repositories, plugin_context.components, plugin_context.clients,
                      plugin_context.cluster_config, plugin_context.cmds, plugin_context.options,
                      plugin_context.stdio, *args, **kwargs)

    stdio = plugin_context.stdio
    cmds = plugin_context.cmds
    if plugin_context.get_variable('primary_info'):
        primary_cluster = plugin_context.get_variable('primary_info').get('primary_deploy_name')
        primary_tenant = plugin_context.get_variable('primary_info').get('primary_tenant')
    else:
        primary_cluster = plugin_context.get_variable('primary_deploy')
        primary_tenant = plugin_context.get_variable('primary_tenant')

    standby_cluster = plugin_context.cluster_config.deploy_name
    standby_tenant = cmds[1]
    standby_cursor = cursors.get(standby_cluster)

    standby_tenant_password = getattr(plugin_context.options, 'tenant_root_password') if getattr(plugin_context.options, 'tenant_root_password') else ''

    plugin_manager = kwargs.get('plugin_manager')
    # for repository in repositories:
    repository = kwargs.get('repository')
    get_standbys_plugin = plugin_manager.get_best_py_script_plugin('get_standbys', repository.name, repository.version)
    ret = call_plugin(get_standbys_plugin, primary_deploy_name=primary_cluster, primary_tenant=primary_tenant, exclude_tenant=[standby_cluster, standby_tenant])
    if not ret:
        error("Find primary tenant {}:{}'s others standby tenants failed".format(primary_cluster, primary_tenant))
        return
    primary_standby_tenants = ret.get_return('standby_tenants')
    stdio.verbose("Primary tenant {}:{}'s others standby tenants:{}".format(primary_cluster, primary_tenant, primary_standby_tenants))
    # 2.find standby tenant`s standby tenant
    get_standbys_plugin = plugin_manager.get_best_py_script_plugin('get_standbys', repository.name, repository.version)
    ret = call_plugin(get_standbys_plugin, primary_deploy_name=standby_cluster, primary_tenant=standby_tenant, exclude_tenant=[primary_cluster, primary_tenant])
    if not ret:
        error("Find primary tenant {}:{}'s others standby tenants failed".format(standby_cluster, standby_tenant))
        return
    standby_standby_tenants = ret.get_return('standby_tenants')
    stdio.verbose("Standby tenant {}:{}'s others standby tenants:{}".format(standby_cluster, standby_tenant, standby_standby_tenants))

    ip_list = get_ip_list(standby_cursor, standby_cluster, standby_tenant, stdio)
    if not ip_list:
        stdio.stop_loading('fail')
        return
    archive_path = plugin_context.get_variable('standby_archive_log_uri')
    primary_archive_path = plugin_context.get_variable('primary_archive_log_uri')
    for tenant_info in primary_standby_tenants:
        deploy_name = tenant_info[0]
        tenant_name = tenant_info[1]
        cursor = cursors.get(deploy_name)
        if not cursor:
            stdio.error("Connect to {} failed.".format(deploy_name))
            return
        res = cursor.fetchone('select TENANT_ROLE,TENANT_ID,COMPATIBILITY_MODE from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (tenant_name, ), raise_exception=False)
        if not res:
            return
        standby_tenant_mode = res['COMPATIBILITY_MODE'].lower()

        sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % res['TENANT_ID']
        res = cursor.fetchone(sql, raise_exception=False)
        if not res:
            stdio.verbose('Select {} log restore source is failed.'.format(deploy_name))
            continue
        if res['TYPE'] == SERVICE_MODE:
            switch_ret = switchover_service_standby(deploy_name, tenant_name, standby_cluster, standby_tenant, standby_tenant_mode)
            if not switch_ret:
                return
        else:
            switch_ret = switchover_location_standby(deploy_name, tenant_name, archive_path)
            if not switch_ret:
                return

    ip_list = get_ip_list(cursors.get(primary_cluster), primary_cluster, primary_tenant, stdio)
    if not ip_list:
        stdio.stop_loading('fail')
        return
    for tenant_info in standby_standby_tenants:
        deploy_name = tenant_info[0]
        tenant_name = tenant_info[1]
        cursor = cursors.get(deploy_name)
        if not cursor:
            stdio.error("Connect to {} failed.".format(deploy_name))
            return
        res = cursor.fetchone('select TENANT_ROLE,TENANT_ID,COMPATIBILITY_MODE from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (tenant_name,), raise_exception=False)
        if not res:
            return
        standby_tenant_mode = res['COMPATIBILITY_MODE'].lower()

        sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % res['TENANT_ID']
        res = cursor.fetchone(sql, raise_exception=False)
        if not res:
            stdio.verbose('Select {} log restore source is failed.'.format(deploy_name))
            continue
        if res['TYPE'] == SERVICE_MODE:
            switch_ret = switchover_service_standby(deploy_name, tenant_name, primary_cluster, primary_tenant, standby_tenant_mode)
            if not switch_ret:
                return
        else:
            switch_ret = switchover_location_standby(deploy_name, tenant_name, primary_archive_path)
            if not switch_ret:
                return

    plugin_context.set_variable('old_primary_standby_tenants', primary_standby_tenants)
    plugin_context.set_variable('old_standby_standby_tenants', standby_standby_tenants)
    stdio.stop_loading('succeed')

    p_mode = plugin_context.get_variable('pre_switchover_p_mode')
    strong_standby = plugin_context.get_variable('pre_switchover_strong_standby')
    strong_standby_deploy = plugin_context.get_variable('pre_switchover_strong_standby_deploy')
    standby_upstream = plugin_context.get_variable('pre_switchover_standby_upstream')

    if p_mode and strong_standby and strong_standby_deploy and 'MAXIMIZE PERFORMANCE' not in p_mode.upper():
        stdio.start_loading('Restore strong sync mode for new primary')
        
        target_strong_partner = None
        target_strong_deploy = None
        tenant_to_clear = None
        tenant_to_clear_deploy = None
        
        if strong_standby == standby_tenant:
            # Case 0: The standby doing the switchover is ITSELF the strong standby.
            # OceanBase automatically maintains the strong sync relationship and protection mode.
            # We don't need to re-execute any ALTER SYSTEM SQLs.
            target_strong_partner = None
            target_strong_deploy = None
            tenant_to_clear = None
            tenant_to_clear_deploy = None
        elif standby_upstream == primary_tenant:
            # Case 1: A weak direct standby switches over. 
            target_strong_partner = None
            target_strong_deploy = None
            tenant_to_clear = strong_standby
            tenant_to_clear_deploy = strong_standby_deploy
        elif standby_upstream == strong_standby:
            # Case 2: A weak cascading standby switches over. Target is master. Clear stand02.
            target_strong_partner = primary_tenant
            target_strong_deploy = primary_cluster
            tenant_to_clear = strong_standby
            tenant_to_clear_deploy = strong_standby_deploy
            
        if target_strong_partner and target_strong_deploy:
            new_primary_cursor = cursors.get(standby_cluster)
            target_cursor = cursors.get(target_strong_deploy)
            
            if new_primary_cursor and target_cursor:
                # 1. Clear old strong sync dest
                if tenant_to_clear and tenant_to_clear_deploy:
                    clear_cursor = cursors.get(tenant_to_clear_deploy)
                    if clear_cursor:
                        try:
                            sql_clear = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % tenant_to_clear
                            clear_cursor.execute(sql_clear, raise_exception=True)
                        except Exception as e:
                            stdio.verbose("Clear old SYNC_STANDBY_DEST for %s failed: %s" % (tenant_to_clear, e))
                
                # 2. Get IP list for target_strong_partner and new_primary
                target_ip_list = get_ip_list(target_cursor, target_strong_deploy, target_strong_partner, stdio)
                new_primary_ip_list = get_ip_list(new_primary_cursor, standby_cluster, standby_tenant, stdio)
                
                if target_ip_list and new_primary_ip_list:
                    def _get_pwd(c_name, t_name):
                        pw = getattr(plugin_context.options, 'standbyro_password', '')
                        if not pw:
                            cfg = cluster_configs.get(c_name)
                            if cfg:
                                pw_dict = cfg.get_component_attr('standbyro_password')
                                if pw_dict:
                                    pw = pw_dict.get(t_name, '')
                        return pw

                    target_pwd = _get_pwd(target_strong_deploy, target_strong_partner)
                    new_primary_pwd = _get_pwd(standby_cluster, standby_tenant)

                    net_timeout_str = ''
                    if 'AVAILABILITY' in p_mode.upper():
                        net_timeout_str = ' NET_TIMEOUT=20'

                    dest_primary = 'SERVICE=%s%s USER=standbyro@%s PASSWORD=%s' % (target_ip_list, net_timeout_str, target_strong_partner, target_pwd)
                    dest_standby = 'SERVICE=%s%s USER=standbyro@%s PASSWORD=%s' % (new_primary_ip_list, net_timeout_str, standby_tenant, new_primary_pwd)
                    
                    try:
                        # 3. New primary sets SYNC_STANDBY_DEST pointing to target
                        sql_primary_dest = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '%s' tenant = '%s'" % (dest_primary, standby_tenant)
                        new_primary_cursor.execute(sql_primary_dest, raise_exception=True)
                        
                        # 4. Target sets SYNC_STANDBY_DEST pointing to new primary
                        sql_standby_dest = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '%s' tenant = '%s'" % (dest_standby, target_strong_partner)
                        target_cursor.execute(sql_standby_dest, raise_exception=True)
                        
                        # 5. New primary sets protection mode
                        # If p_mode is MAXIMIZE PROTECTION or MAXIMIZE AVAILABILITY, this will set it accordingly.
                        set_mode_sql = "ALTER SYSTEM SET STANDBY TENANT TO %s tenant = '%s'" % (p_mode.upper().replace('MAXIMUM', 'MAXIMIZE'), standby_tenant)
                        
                        # In the special case where target is the old primary and we need to establish strong sync, 
                        # we must also ensure target's mode is set to PERFORMANCE first (it usually falls back, but let's be safe) 
                        # before New Primary can elevate it. Wait, OceanBase handles the Standby side automatically when Primary sets it.
                        new_primary_cursor.execute(set_mode_sql, raise_exception=True)
                        
                        stdio.stop_loading('succeed')
                    except Exception as e:
                        stdio.error("Restore strong sync failed: %s" % e)
                        stdio.stop_loading('fail')
                else:
                    stdio.stop_loading('fail')
                    stdio.error("Failed to get IP list for strong sync restore.")
            else:
                stdio.stop_loading('fail')
                stdio.error("Failed to get cursors for strong sync restore.")
        else:
            if tenant_to_clear and tenant_to_clear_deploy:
                clear_cursor = cursors.get(tenant_to_clear_deploy)
                if clear_cursor:
                    try:
                        sql_clear = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % tenant_to_clear
                        clear_cursor.execute(sql_clear, raise_exception=True)
                        stdio.verbose("Cleared SYNC_STANDBY_DEST for old strong standby %s" % tenant_to_clear)
                    except Exception as e:
                        stdio.verbose("Clear old SYNC_STANDBY_DEST for %s failed: %s" % (tenant_to_clear, e))
                
                primary_cursor = cursors.get(primary_cluster)
                if primary_cursor:
                    try:
                        sql_clear_pri = "ALTER SYSTEM SET SYNC_STANDBY_DEST = '' tenant = '%s'" % primary_tenant
                        primary_cursor.execute(sql_clear_pri, raise_exception=True)
                        stdio.verbose("Cleared SYNC_STANDBY_DEST for old primary %s" % primary_tenant)
                    except Exception as e:
                        stdio.verbose("Clear SYNC_STANDBY_DEST for old primary %s failed: %s" % (primary_tenant, e))
                        
                new_primary_cursor = cursors.get(standby_cluster)
                if new_primary_cursor:
                    try:
                        sql_downgrade = "ALTER SYSTEM SET STANDBY TENANT TO MAXIMIZE PERFORMANCE tenant = '%s'" % standby_tenant
                        new_primary_cursor.execute(sql_downgrade, raise_exception=True)
                        stdio.verbose("Downgraded new primary %s to MAXIMIZE PERFORMANCE" % standby_tenant)
                    except Exception as e:
                        stdio.verbose("Downgrade new primary %s failed: %s" % (standby_tenant, e))

            stdio.stop_loading('succeed')

    return plugin_context.return_true()