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
import re
from const import LOCATION_MODE, SERVICE_MODE

def get_backup_and_archive_uri(path):
    if 'oss' in path:
        uri_pattern = r'oss://.*?access_key=[^&]*'
    elif 'amazonaws' in path:
        uri_pattern = r's3://.*?s3_region=[^&]*'
    else:
        uri_pattern = r's3://.*?access_key=[^&]*'
    match = re.search(uri_pattern, path)
    if match:
        return match.group()

def get_all_parent_paths(path):
    path = os.path.abspath(path)
    current_path = path
    parent_paths = []

    while current_path != os.path.dirname(current_path):
        parent_paths.append(current_path)
        current_path = os.path.dirname(current_path)

    parent_paths.append(current_path)
    return parent_paths


def check_nfs_path(paths, client):
    for path in paths:
        ret = client.execute_command('df -T %s | grep nfs' % path)
        if ret and ret.stdout.strip().find(path):
            break
    else:
        return False
    return True

def standby_uri_check(plugin_context, cursors={}, cluster_configs={}, relation_tenants={}, *args, **kwargs):
    def get_uri(cursor, uri_type, tenant_id, tenant):
        if option_mode == 'switchover':
            err_msg = "Set up backup and archiving for %s" % tenant
        else:
            err_msg = "Rerun with " + '--data_backup_uri' if uri_type == 'backup' else '--archive_log_uri' + " or set up backup and archiving for %s" % tenant

        if uri_type == 'backup':
            sql = 'SELECT VALUE FROM oceanbase.CDB_OB_BACKUP_PARAMETER WHERE TENANT_ID=%s' % tenant_id
            res = cursor.fetchone(sql)
            if not res or res['VALUE'] is None:
                error(err_msg)
                return None
        else:
            sql = "SELECT VALUE FROM oceanbase.CDB_OB_ARCHIVE_DEST WHERE TENANT_ID=%s AND NAME='path'" % tenant_id
            res = cursor.fetchone(sql)
            if not res or res['VALUE'] is None:
                error(err_msg)
                return None
        data_uri = res['VALUE']
        if data_uri.startswith(('oss://', 's3://')):
            data_uri = get_backup_and_archive_uri(data_uri)
        return data_uri

    def check_nfs_uri(uri):
        all_path = get_all_parent_paths(uri[len('file://'):])
        for server in plugin_context.cluster_config.servers:
            client = clients[server]
            if not check_nfs_path(all_path, client):
                if len(plugin_context.cluster_config.servers) > 1:
                    stdio.error("data_backup_uri and archive_log_uri must in the nfs.")
                    return False
            return True


    def error(msg='', *arg, **kwargs):
        stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('failed')

    def get_primary_id(primary_cursor, tenant_name):
        sql = 'select tenant_id from oceanbase.__all_tenant where tenant_name=%s'
        primary_tenant_info = primary_cursor.fetchone(sql, (tenant_name, ))
        if not primary_tenant_info:
            stdio.error('Primary tenant {}:{} is not exist.'.format(primary_deploy_name, tenant_name))
            return None
        return primary_tenant_info['tenant_id']


    options = plugin_context.options
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    cmds = plugin_context.cmds

    data_backup_uri = getattr(options, 'data_backup_uri', None)
    archive_log_uri = getattr(options, 'archive_log_uri', None)
    option_mode = kwargs.get('option_mode')
    standby_type = plugin_context.get_variable("source_type") if option_mode == 'switchover' else getattr(options, 'type')
    plugin_context.set_variable('get_backup_and_archive_uri', get_backup_and_archive_uri)

    stdio.start_loading("standby uri checking")
    
    if option_mode in ['log_source', 'switchover']:
        standby_deploy_name = plugin_context.cluster_config.deploy_name
        standby_tenant = cmds[1]
        standby_cursor = cursors.get(standby_deploy_name)

        if not standby_cursor:
            error('Failed to connect standby deploy: {}.'.format(standby_deploy_name))
            return False
        
        sql = "select TENANT_ROLE,TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
        tenant_role_res = standby_cursor.fetchone(sql, (standby_tenant, ), raise_exception=True)
        if not tenant_role_res:
            error("{}:{} not exists".format(standby_deploy_name, standby_tenant))
            return
        if tenant_role_res['TENANT_ROLE'] != 'STANDBY':
            error("{}:{} is not standby tenant.".format(standby_deploy_name, standby_tenant))
            return

        uri_check = plugin_context.get_variable('check_uri')
        if (option_mode == 'switchover' and standby_type == LOCATION_MODE) or uri_check:
            standby_archive_log_uri = get_uri(standby_cursor, 'archive', tenant_role_res['TENANT_ID'], standby_tenant)
            if not standby_archive_log_uri:
                stdio.stop_loading('failed')
                return plugin_context.return_false()
            if standby_archive_log_uri and standby_archive_log_uri.startswith('file://') and not check_nfs_uri(standby_archive_log_uri):
                stdio.stop_loading('failed')
                return plugin_context.return_false()
            plugin_context.set_variable('standby_archive_log_uri', standby_archive_log_uri)

            standby_data_backup_uri = get_uri(standby_cursor, 'backup', tenant_role_res['TENANT_ID'], standby_tenant)
            if not standby_data_backup_uri:
                stdio.stop_loading('failed')
                return plugin_context.return_false()
            if standby_data_backup_uri and standby_data_backup_uri.startswith('file://') and not check_nfs_uri(standby_data_backup_uri):
                return plugin_context.return_false()
            plugin_context.set_variable('standby_data_backup_uri', standby_data_backup_uri)

            primary_cursor = plugin_context.get_variable('primary_tenant_cursor')
            primary_tenant = plugin_context.get_variable('primary_tenant')
            primary_id = plugin_context.get_variable('primary_tenant_id')
            primary_archive_log_uri = get_uri(primary_cursor, 'archive', primary_id, primary_tenant)
            if not primary_archive_log_uri:
                stdio.stop_loading('failed')
                return plugin_context.return_false()
            if primary_archive_log_uri and primary_archive_log_uri.startswith('file://') and not check_nfs_uri(primary_archive_log_uri):
                stdio.stop_loading('failed')
                return plugin_context.return_false()
            plugin_context.set_variable('primary_archive_log_uri', primary_archive_log_uri)

            primary_data_backup_uri = get_uri(primary_cursor, 'backup', primary_id, primary_tenant)
            if not primary_data_backup_uri:
                stdio.stop_loading('failed')
                return plugin_context.return_false()
            if primary_data_backup_uri and primary_data_backup_uri.startswith('file://') and not check_nfs_uri(primary_data_backup_uri):
                return plugin_context.return_false()
            plugin_context.set_variable('primary_data_backup_uri', primary_data_backup_uri)

            if uri_check:
                check_cursor = plugin_context.get_variable('check_tenant_cursor')
                check_tenant = plugin_context.get_variable('check_tenant')
                check_id = plugin_context.get_variable('check_tenant_id')
                check_archive_log_uri = get_uri(check_cursor, 'archive', check_id, check_tenant)
                if not check_archive_log_uri:
                    stdio.stop_loading('failed')
                    return plugin_context.return_false()
                if check_archive_log_uri and check_archive_log_uri.startswith('file://') and not check_nfs_uri(check_archive_log_uri):
                    stdio.stop_loading('failed')
                    return plugin_context.return_false()

                check_data_backup_uri = get_uri(check_cursor, 'backup', check_id, check_tenant)
                if not check_data_backup_uri:
                    stdio.stop_loading('failed')
                    return plugin_context.return_false()
                if check_data_backup_uri and check_data_backup_uri.startswith('file://') and not check_nfs_uri(check_data_backup_uri):
                    return plugin_context.return_false()

            stdio.stop_loading('succeed')
            return plugin_context.return_true()
        
        if standby_type == SERVICE_MODE:
            stdio.stop_loading('succeed')
            return plugin_context.return_true()
    
    elif option_mode in ['create_standby_tenant']:
        primary_deploy_name = cmds[1]
        primary_tenant = cmds[2]
        primary_cursor = cursors.get(primary_deploy_name)
        primary_tenant_id = get_primary_id(primary_cursor, primary_tenant)
        if not primary_tenant_id:
            return

        sql = "SELECT STATUS FROM oceanbase.CDB_OB_BACKUP_JOBS WHERE TENANT_ID = %s" % primary_tenant_id
        res = primary_cursor.fetchone(sql)
        if res is False:
            error(f"Failed to query {primary_tenant} backup status")
            return
        if res:
            error(f"The {primary_tenant} tenant has not completed the backup yet. Please try again later.")
            return
        
    if option_mode == "log_source":
        primary_cursor = plugin_context.get_variable("primary_cursor")
        primary_tenant_id = plugin_context.get_variable("primary_tenant_id")
        primary_tenant = plugin_context.get_variable("primary_tenant")
    if not archive_log_uri:
        archive_log_uri = get_uri(primary_cursor, 'archive', primary_tenant_id, primary_tenant)
        if not archive_log_uri:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    if archive_log_uri and archive_log_uri.startswith('file://') and not check_nfs_uri(archive_log_uri):
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    plugin_context.set_variable('archive_log_uri', archive_log_uri)
    
    if kwargs.get('option_mode') == 'log_source':
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    
    if not data_backup_uri:
        data_backup_uri = get_uri(primary_cursor, 'backup', primary_tenant_id, primary_tenant)
        if not data_backup_uri:
            stdio.stop_loading('failed')
            return plugin_context.return_false()
    if data_backup_uri and data_backup_uri.startswith('file://') and not check_nfs_uri(data_backup_uri):
        return plugin_context.return_false()

    plugin_context.set_variable('data_backup_uri', data_backup_uri)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()