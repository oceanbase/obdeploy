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
import time


def _get_cluster_endpoint(cluster_config):
    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf_with_default(server)
    global_config = cluster_config.get_global_conf() or {}
    root_password = server_config.get('root_password')
    if root_password is None:
        root_password = global_config.get('root_password', '')
    return {
        'ip': server.ip,
        'obshell_port': int(server_config.get('obshell_port', 2886)),
        'rpc_port': int(server_config.get('rpc_port', 2882)),
        'root_password': root_password or '',
    }


def _new_obshell_client(cluster_meta):
    from obshell import ClientSet, ClientV1
    from obshell.auth import PasswordAuth
    from obshell.request import ProtocolOptions

    client_set = ClientSet(
        cluster_meta['ip'],
        cluster_meta['obshell_port'],
        PasswordAuth(cluster_meta['root_password']),
    )
    client = client_set.v1
    try:
        client.get_info()
        return client
    except Exception as e:
        match = re.search(r'status code: (\d+)', str(e))
        if not match or match.group(1) != '400':
            raise

    client = ClientV1(
        cluster_meta['ip'],
        cluster_meta['obshell_port'],
        PasswordAuth(cluster_meta['root_password']),
        protocol_options=ProtocolOptions.https_insecure(),
    )
    client.get_info()
    return client


def _reparent_cascading_standby(plugin_context, primary_cursor, standby_meta):
    stdio = plugin_context.stdio
    sql = "alter system set log_restore_source = '{}:{}'".format(
        standby_meta['ip'], standby_meta['rpc_port'])
    try:
        primary_cursor.execute(sql, raise_exception=True, stdio=stdio)
    except Exception as e:
        stdio.error('Failed to update the cascading standby log_restore_source: %s' % e)
        return False
    plugin_context.set_variable('seekdb_is_standby', True)
    return True


def _role(cursor, reconnect=False):
    query_cursor = cursor
    if reconnect:
        query_cursor = cursor.new_cursor(
            tenant='',
            password=cursor.password,
            print_exception=False,
        )
        if not query_cursor:
            return None
    try:
        result = query_cursor.fetchone(
            'SELECT ROLE FROM oceanbase.__all_virtual_server_stat',
            raise_exception=False,
        )
        if not result:
            return None
        return result.get('ROLE') or result.get('role')
    finally:
        if query_cursor is not cursor:
            query_cursor.close()


def _wait_for_switched_roles(primary_cursor, standby_cursor, timeout=30, interval=1):
    deadline = time.time() + timeout
    while True:
        if (_role(primary_cursor, reconnect=True) == 'STANDBY'
                and _role(standby_cursor, reconnect=True) == 'PRIMARY'):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(interval)


def switchover(plugin_context, cursors=None, cluster_configs=None, *args, **kwargs):
    stdio = plugin_context.stdio
    cursors = cursors or {}
    cluster_configs = cluster_configs or {}
    primary_deploy_name = plugin_context.get_variable('primary_deploy_name')
    standby_deploy_name = plugin_context.get_variable('standby_deploy_name')

    stdio.start_loading('Switchover cluster through OBShell')
    if not primary_deploy_name or not standby_deploy_name:
        stdio.error('Primary or Standby deploy name not found in context.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    primary_config = cluster_configs.get(primary_deploy_name)
    standby_config = cluster_configs.get(standby_deploy_name)
    if not primary_config or not standby_config:
        stdio.error('Failed to load primary or standby seekdb configuration.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    primary_cursor = cursors.get(primary_deploy_name)
    standby_cursor = cursors.get(standby_deploy_name)
    if not primary_cursor:
        stdio.error('Failed to connect primary deploy: %s.' % primary_deploy_name)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    primary_role = _role(primary_cursor)
    if not primary_role:
        stdio.error('Failed to get cluster role for %s.' % primary_deploy_name)
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    standby_meta = _get_cluster_endpoint(standby_config)
    if primary_role == 'STANDBY':
        if not _reparent_cascading_standby(plugin_context, primary_cursor, standby_meta):
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        plugin_context.set_variable('switchover_success', True)
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    if primary_role != 'PRIMARY':
        stdio.error('Unknown cluster role %s for %s.' % (
            primary_role, primary_deploy_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    primary_meta = _get_cluster_endpoint(primary_config)
    try:
        client = _new_obshell_client(primary_meta)
        switchover_sync = getattr(client, 'switchover_seekdb_standby_sync', None)
        if not callable(switchover_sync):
            raise RuntimeError(
                'The installed obshell Python SDK does not support seekdb switchover. '
                'Please install an SDK containing switchover_seekdb_standby_sync.')
        switchover_sync(standby_meta['ip'], standby_meta['obshell_port'])
    except Exception as e:
        if standby_cursor and _wait_for_switched_roles(primary_cursor, standby_cursor):
            stdio.warn(
                'OBShell reported a switchover error after both cluster roles were switched: %s. '
                'Continuing to update the OBD topology.' % e
            )
        else:
            stdio.error(
                'OBShell switchover failed on %s:%s: %s'
                % (primary_meta['ip'], primary_meta['obshell_port'], e)
            )
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    plugin_context.set_variable('switchover_success', True)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
