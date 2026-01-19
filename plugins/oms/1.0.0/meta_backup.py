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

from tool import Cursor, get_metadb_info_from_depends_ob, get_option, docker_run_sudo_prefix


def meta_backup(plugin_context, backup_path=None, enable_backup=True, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    global_config = cluster_config.get_original_global_conf()
    options = plugin_context.options

    backup_path = get_option(options, 'oms_backup_path', backup_path)
    disable_oms_backup = get_option(options, 'disable_oms_backup', None)
    if disable_oms_backup:
        enable_backup = False

    if not enable_backup:
        stdio.verbose('backup disabled, skip backup procedure')
        return plugin_context.return_true()

    if not backup_path:
        backup_path = os.path.join(os.path.expanduser('~'), 'oms', 'meta_backup_data')

    # Check mysqldump tool in docker container on first OMS node
    stdio.start_loading('Check mysqldump tool')
    first_server = cluster_config.servers[0]
    client = clients[first_server]
    container_name = global_config.get('container_name')
    prefix = docker_run_sudo_prefix(client)
    # Check if mysqldump exists in docker container
    check_cmd = f"{prefix}docker exec {container_name} which mysqldump"
    if not client.execute_command(check_cmd):
        stdio.stop_loading('fail')
        stdio.error(f'{first_server.ip}: mysqldump is not installed in docker container {container_name}')
        return plugin_context.return_false()
    stdio.stop_loading('succeed')

    ob_metadb_info = get_metadb_info_from_depends_ob(cluster_config, stdio)
    if ob_metadb_info:
        oms_meta_host = ob_metadb_info['host']
        oms_meta_port = ob_metadb_info['port']
        oms_meta_user = ob_metadb_info['user']
        oms_meta_password = ob_metadb_info['password']
    else:
        oms_meta_host = global_config.get('oms_meta_host')
        oms_meta_port = global_config.get('oms_meta_port')
        oms_meta_user = global_config.get('oms_meta_user')
        oms_meta_password = global_config.get('oms_meta_password')

    if not all([oms_meta_host, oms_meta_port, oms_meta_user, oms_meta_password]):
        stdio.error('OMS meta database connection info is incomplete')
        return plugin_context.return_false()

    # Collect databases to backup
    databases_to_backup = []
    drc_rm_db = global_config.get('drc_rm_db', 'oms_rm')
    drc_cm_db = global_config.get('drc_cm_db', 'oms_cm')
    if drc_cm_db:
        databases_to_backup.append(drc_cm_db)
    if drc_rm_db:
        databases_to_backup.append(drc_rm_db)
    
    # Collect drc_cm_heartbeat_db from regions
    regions = global_config.get('regions', [])
    drc_cm_heartbeat_dbs = set()
    for region in regions:
        drc_cm_heartbeat_db = region.get('drc_cm_heartbeat_db') or (global_config.get('drc_cm_heartbeat_db', 'oms_cm_heartbeat') + "_" + str(region.get('cm_location', '')))
        if drc_cm_heartbeat_db:
            drc_cm_heartbeat_dbs.add(drc_cm_heartbeat_db)
    
    databases_to_backup.extend(list(drc_cm_heartbeat_dbs))

    if not databases_to_backup:
        stdio.error('No databases to backup')
        return plugin_context.return_false()

    # Clean up heatbeat_sequence in each drc_cm_heartbeat_db before backup
    if drc_cm_heartbeat_dbs:
        stdio.start_loading('Clean up heatbeat_sequence in drc_cm_heartbeat_db')
        try:
            cursor = Cursor(ip=oms_meta_host,
                          user=oms_meta_user,
                          port=int(oms_meta_port),
                          tenant='',
                          password=oms_meta_password,
                          stdio=stdio)
            
            for drc_cm_heartbeat_db in drc_cm_heartbeat_dbs:
                try:
                    cursor.execute('use %s' % drc_cm_heartbeat_db)
                    cursor.execute('delete from heatbeat_sequence where id < (select max(id) from heatbeat_sequence);', exc_level='warn')
                    stdio.verbose('Cleaned up heatbeat_sequence in %s' % drc_cm_heartbeat_db)
                except Exception as e:
                    stdio.warn('Failed to clean up heatbeat_sequence in %s: %s' % (drc_cm_heartbeat_db, e))
                    # Continue with other databases even if one fails
            
            stdio.stop_loading('succeed')
        except Exception as e:
            stdio.stop_loading('fail')
            stdio.error('Failed to connect to database for cleanup: %s' % e)
            return plugin_context.return_false()

    back_files_map = {database_name: os.path.join(backup_path, f'{database_name}_backup.sql') for database_name in databases_to_backup}

    # Execute mysqldump to backup databases
    stdio.start_loading('Backup OMS meta databases using mysqldump')
    try:
        # Use first server's client and container
        first_server = cluster_config.servers[0]
        client = clients[first_server]
        container_name = global_config.get('container_name')
        prefix = docker_run_sudo_prefix(client)
        
        for database_name, backup_file in back_files_map.items():
            # Build mysqldump command
            mysqldump_cmd = f"mysqldump -h {oms_meta_host} -u {oms_meta_user} -P {oms_meta_port} -p{oms_meta_password} --triggers=false --single-transaction {database_name}"
            
            # Build docker exec command
            docker_exec_cmd = f"{prefix}docker exec {container_name} {mysqldump_cmd}"
            # Execute docker exec command
            ret = client.execute_command(docker_exec_cmd, stdio=stdio)
            if not ret:
                stdio.stop_loading('fail')
                error_msg = ret.stderr if hasattr(ret, 'stderr') and ret.stderr else 'Unknown error'
                stdio.error('mysqldump execution failed: %s' % error_msg)
                break
            try:
                if not os.path.isdir(backup_path):
                    os.makedirs(backup_path)
            except Exception as e:
                stdio.error('Prepare backup path failed: %s' % e)
                return plugin_context.return_false()

            with open(backup_file, 'w') as f:
                f.write(ret.stdout)
            
            stdio.verbose(f'Backed up {database_name} to {backup_file}')

    except Exception as e:
        stdio.stop_loading('fail')
        stdio.error('Backup execution failed: %s' % e)
        return plugin_context.return_false()

    stdio.stop_loading('succeed')

    return plugin_context.return_true()


