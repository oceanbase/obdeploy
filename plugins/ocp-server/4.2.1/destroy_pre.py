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

import re
from tool import Cursor


def destroy_pre(plugin_context, *args, **kwargs):
    def clean_database(cursor, database):
        database = quote_identifier(database)
        if not cursor.execute("drop database {0}".format(database)):
            return False
        return bool(cursor.execute("create database if not exists {0}".format(database)))

    def quote_identifier(identifier):
        if not identifier or not re.match(r'^[A-Za-z_][A-Za-z0-9_$]*$', identifier):
            raise ValueError('invalid OceanBase identifier: {0}'.format(identifier))
        return '`{0}`'.format(identifier)

    def get_row_value(row, *keys):
        for key in keys:
            if key in row:
                return row[key]

    def persist_cleanup_state(tenant_key, tenant_config):
        return cluster_config.update_global_conf(tenant_key, tenant_config)

    def capture_cleanup_state(cursor, tenant_key, tenant_config, tenant_id):
        pools = cursor.fetchall(
            "select RESOURCE_POOL_ID, NAME, UNIT_CONFIG_ID "
            "from oceanbase.DBA_OB_RESOURCE_POOLS where TENANT_ID = %s",
            [tenant_id])
        if pools is False:
            return False

        pool_states = []
        unit_config_ids = set()
        for pool in pools:
            pool_name = get_row_value(pool, 'NAME', 'name')
            resource_pool_id = get_row_value(
                pool, 'RESOURCE_POOL_ID', 'resource_pool_id')
            unit_config_id = get_row_value(pool, 'UNIT_CONFIG_ID', 'unit_config_id')
            quote_identifier(pool_name)
            if resource_pool_id is None or unit_config_id is None:
                return False
            pool_states.append({
                'name': pool_name, 'resource_pool_id': resource_pool_id,
                'unit_config_id': unit_config_id})
            unit_config_ids.add(unit_config_id)

        unit_states = []
        for unit_config_id in unit_config_ids:
            unit = cursor.fetchone(
                "select NAME from oceanbase.DBA_OB_UNIT_CONFIGS where UNIT_CONFIG_ID = %s",
                [unit_config_id])
            if unit is False:
                return False
            if unit:
                unit_name = get_row_value(unit, 'NAME', 'name')
                quote_identifier(unit_name)
                unit_states.append({
                    'name': unit_name,
                    'unit_config_id': unit_config_id})

        tenant_config['cleanup_resources'] = {
            'resource_pools': pool_states,
            'resource_units': unit_states}
        return persist_cleanup_state(tenant_key, tenant_config)

    def clean_captured_resources(cursor, tenant_key, tenant_config):
        cleanup_resources = tenant_config.get('cleanup_resources')
        if not cleanup_resources:
            return True

        success = True
        remaining_pools = []
        for pool_state in cleanup_resources.get('resource_pools', []):
            pool_name = pool_state['name']
            pool = cursor.fetchone(
                "select NAME, UNIT_CONFIG_ID from oceanbase.DBA_OB_RESOURCE_POOLS "
                "where RESOURCE_POOL_ID = %s",
                [pool_state['resource_pool_id']])
            if pool is False:
                success = False
                remaining_pools.append(pool_state)
            elif pool:
                current_name = get_row_value(pool, 'NAME', 'name')
                current_unit_config_id = get_row_value(
                    pool, 'UNIT_CONFIG_ID', 'unit_config_id')
                if current_name != pool_name or str(current_unit_config_id) != str(
                        pool_state['unit_config_id']):
                    stdio.error(
                        'resource pool {0} identity changed, skip deleting it'.format(
                            pool_name))
                    success = False
                    remaining_pools.append(pool_state)
                elif not cursor.execute(
                        "drop resource pool {0}".format(
                            quote_identifier(pool_name))):
                    success = False
                    remaining_pools.append(pool_state)

        remaining_units = []
        for unit_state in cleanup_resources.get('resource_units', []):
            unit_config_id = unit_state['unit_config_id']
            if any(str(pool_state['unit_config_id']) == str(unit_config_id)
                   for pool_state in remaining_pools):
                remaining_units.append(unit_state)
                continue
            pool_count = cursor.fetchone(
                "select count(*) as POOL_COUNT from oceanbase.DBA_OB_RESOURCE_POOLS where UNIT_CONFIG_ID = %s",
                [unit_config_id])
            if pool_count is False:
                success = False
                remaining_units.append(unit_state)
                continue
            if get_row_value(pool_count, 'POOL_COUNT', 'pool_count'):
                continue
            unit = cursor.fetchone(
                "select NAME from oceanbase.DBA_OB_UNIT_CONFIGS where UNIT_CONFIG_ID = %s",
                [unit_config_id])
            if unit is False:
                success = False
                remaining_units.append(unit_state)
            elif unit:
                current_name = get_row_value(unit, 'NAME', 'name')
                if current_name != unit_state['name']:
                    stdio.error(
                        'resource unit {0} identity changed, skip deleting it'.format(
                            unit_state['name']))
                    success = False
                    remaining_units.append(unit_state)
                elif not cursor.execute(
                        "drop resource unit {0}".format(
                            quote_identifier(unit_state['name']))):
                    success = False
                    remaining_units.append(unit_state)

        if remaining_pools or remaining_units:
            tenant_config['cleanup_resources'] = {
                'resource_pools': remaining_pools,
                'resource_units': remaining_units}
        else:
            tenant_config.pop('cleanup_resources', None)
        if not persist_cleanup_state(tenant_key, tenant_config):
            return False
        return success and not remaining_pools and not remaining_units

    def clean_tenant(cursor, tenant_key, tenant_config):
        tenant_name = tenant_config['tenant_name']
        recorded_tenant_id = tenant_config['tenant_id']
        tenant = cursor.fetchone(
            "select TENANT_ID from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s",
            [tenant_name])
        if tenant is False:
            return False
        if not tenant:
            stdio.verbose(
                'tenant {0} does not exist, continue captured resource cleanup'.format(
                    tenant_name))
            return clean_captured_resources(cursor, tenant_key, tenant_config)

        tenant_id = get_row_value(tenant, 'TENANT_ID', 'tenant_id')
        if str(tenant_id) != str(recorded_tenant_id):
            stdio.error(
                'tenant {0} id changed from {1} to {2}, skip deleting it'.format(
                    tenant_name, recorded_tenant_id, tenant_id))
            return False

        if not tenant_config.get('cleanup_resources') and not capture_cleanup_state(
                cursor, tenant_key, tenant_config, tenant_id):
            return False
        if not cursor.execute("drop tenant {0} FORCE".format(quote_identifier(tenant_name))):
            return False
        return clean_captured_resources(cursor, tenant_key, tenant_config)

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    removed_components = cluster_config.get_deploy_removed_components()
    clean_data = (not cluster_config.depends or len(removed_components) > 0 and len(removed_components.intersection({"oceanbase", "oceanbase-ce"})) == 0) and stdio.confirm("Would you like to clean meta data")

    plugin_context.set_variable("clean_dirs", ['log_dir', 'soft_dir'])
    sudo_command = {}
    clients = plugin_context.clients
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        if not client.execute_command('[ `id -u` == "0" ]') and server_config.get('launch_user', '') and client.execute_command('sudo -n true'):
            sudo_command[server] = "sudo "
    if sudo_command:
        plugin_context.set_variable("sudo_command", sudo_command)

    if not clean_data:
        return plugin_context.return_true()

    stdio.start_loading('ocp-server metadb and monitordb cleaning')
    success = True
    try:
        env = plugin_context.get_variable('start_env')
        if not env:
            stdio.stop_loading('succeed')
            return plugin_context.return_true()

        server_config = env[cluster_config.servers[0]]
        jdbc_url = server_config['jdbc_url']
        matched = re.match(r"^jdbc:\S+://(\S+?)(|:\d+)/(\S+)", jdbc_url)
        if not matched:
            raise ValueError('jdbc_url is not valid')
        host = matched.group(1)
        port = matched.group(2)[1:]

        if not cluster_config.depends:
            tenant_configs = [
                ('ocp_meta_tenant', server_config['ocp_meta_tenant'], 'ocp_meta_username',
                 'ocp_meta_password', 'ocp_meta_db'),
                ('ocp_monitor_tenant', server_config['ocp_monitor_tenant'], 'ocp_monitor_username',
                 'ocp_monitor_password', 'ocp_monitor_db')]
            system_cursor = None
            cleaned_tenants = set()
            for tenant_key, tenant_config, user_key, password_key, database_key in tenant_configs:
                tenant_name = tenant_config['tenant_name']
                recorded_tenant_id = tenant_config.get('tenant_id')
                if tenant_config.get('created_by_obd', False) and recorded_tenant_id is not None:
                    if tenant_name in cleaned_tenants:
                        continue
                    cleaned_tenants.add(tenant_name)
                    if system_cursor is None:
                        system_cursor = Cursor(
                            host, port, user=server_config['jdbc_username'],
                            password=server_config['jdbc_password'], stdio=stdio)
                    stdio.verbose("clean tenant {0}".format(tenant_name))
                    if not clean_tenant(system_cursor, tenant_key, tenant_config):
                        success = False
                else:
                    stdio.verbose("clean database {0} in retained tenant {1}".format(
                        server_config[database_key], tenant_name))
                    tenant_cursor = Cursor(
                        host, port, user=server_config[user_key], tenant=tenant_name,
                        password=server_config[password_key], stdio=stdio)
                    if not clean_database(tenant_cursor, server_config[database_key]):
                        success = False
        else:
            stdio.verbose("clean metadb")
            meta_cursor = Cursor(host, port, user=server_config['ocp_meta_username'], tenant=server_config['ocp_meta_tenant']['tenant_name'], password=server_config['ocp_meta_password'], stdio=stdio)
            if not clean_database(meta_cursor, server_config['ocp_meta_db']):
                success = False
            stdio.verbose("clean monitordb")
            monitor_cursor = Cursor(host, port, user=server_config['ocp_monitor_username'], tenant=server_config['ocp_monitor_tenant']['tenant_name'], password=server_config['ocp_monitor_password'], stdio=stdio)
            if not clean_database(monitor_cursor, server_config['ocp_monitor_db']):
                success = False
    except Exception:
        stdio.error("failed to clean meta and monitor data")
        success = False

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
    return plugin_context.return_false()
