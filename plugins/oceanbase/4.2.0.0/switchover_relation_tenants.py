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
    def switchover_service_standby(deploy_name, tenant_name, primary_cluster, primary_tenant):
        deploy_config = cluster_configs.get(deploy_name)
        if deploy_config:
            standbyro_password_dict = deploy_config.get_component_attr('standbyro_password')
            if standbyro_password_dict:
                standbyro_password = standbyro_password_dict.get(tenant_name)
                if standbyro_password:
                    setattr(plugin_context.options, 'standbyro_password', standbyro_password)
                        
        plugin_context.set_variable('switchover_cluster', primary_cluster)
        plugin_context.set_variable('switchover_tenant', primary_tenant)
        create_standbypro_plugin = plugin_manager.get_best_py_script_plugin('create_standbyro', repository.name, repository.version)
        ret = call_plugin(create_standbypro_plugin, option_mode='switchover')
        if not ret:
            error("The primary tenant {}:{} create standbyro user failed".format(primary_cluster, primary_tenant))
            return False
        standbyro_password = plugin_context.get_variable('standbyro_password')
        sql = 'ALTER SYSTEM SET LOG_RESTORE_SOURCE = "SERVICE={} USER=standbyro@{} PASSWORD={}"'.format(ip_list, primary_tenant, standbyro_password)
        try:
            exec_sql_in_tenant(sql, cursors.get(deploy_name), tenant_name, 'mysql', user='root', password=standby_tenant_password, raise_exception=True, retries=5)
        except Exception as e:
            retry_message = 'After resolving the issue, you can retry by manually executing SQL:\'{}\' with the root user in the tenant {}:{}.'.format(sql, deploy_name, tenant_name)
            stdio.exception("Set the old primary`s standby tenant {}:{} as a standby tenant of the new primary`s standby tenant {}:{} failed:{}. \n {}".format(deploy_name, tenant_name, deploy_name, primary_tenant, e, retry_message))
            return False

        dump_standbyro_password_plugin = plugin_manager.get_best_py_script_plugin('dump_standbyro_password', repository.name, repository.version)
        ret = call_plugin(dump_standbyro_password_plugin, dump_cluster=cluster_configs.get(deploy_name), dump_tenant=tenant_name)
        if not ret:
            error("The primary tenant {}:{} dump standbyro password failed".format(deploy_name, tenant_name))
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
                tenant_cursor = cursor.new_cursor(tenant=tenant, user=user, password=password, ip=tenant_ip, port=tenant_port, print_exception=raise_exception)
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
        res = cursor.fetchone('select TENANT_ROLE,TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (tenant_name, ), raise_exception=False)
        if not res:
            return

        sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % res['TENANT_ID']
        res = cursor.fetchone(sql, raise_exception=False)
        if not res:
            stdio.verbose('Select {} log restore source is failed.'.format(deploy_name))
            continue
        if res['TYPE'] == SERVICE_MODE:
            switch_ret = switchover_service_standby(deploy_name, tenant_name, standby_cluster, standby_tenant)
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
        res = cursor.fetchone('select TENANT_ROLE,TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s', (tenant_name,), raise_exception=False)
        if not res:
            return

        sql = 'SELECT TYPE FROM oceanbase.CDB_OB_LOG_RESTORE_SOURCE where TENANT_ID=%s' % res['TENANT_ID']
        res = cursor.fetchone(sql, raise_exception=False)
        if not res:
            stdio.verbose('Select {} log restore source is failed.'.format(deploy_name))
            continue
        if res['TYPE'] == SERVICE_MODE:
            switch_ret = switchover_service_standby(deploy_name, tenant_name, primary_cluster, primary_tenant)
            if not switch_ret:
                return
        else:
            switch_ret = switchover_location_standby(deploy_name, tenant_name, primary_archive_path)
            if not switch_ret:
                return

    plugin_context.set_variable('old_primary_standby_tenants', primary_standby_tenants)
    plugin_context.set_variable('old_standby_standby_tenants', standby_standby_tenants)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()