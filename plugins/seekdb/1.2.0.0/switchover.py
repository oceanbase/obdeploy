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

def switchover(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    stdio = plugin_context.stdio
    primary_deploy_name = plugin_context.get_variable('primary_deploy_name')
    standby_deploy_name = plugin_context.get_variable('standby_deploy_name')
    
    stdio.start_loading('Switchover cluster')
    if not primary_deploy_name or not standby_deploy_name:
        stdio.error("Primary or Standby deploy name not found in context.")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    primary_cursor = cursors.get(primary_deploy_name)
    standby_cursor = cursors.get(standby_deploy_name)

    cluster_config = plugin_context.cluster_config
    server = cluster_config.servers[0]
    server_conf = cluster_config.get_server_conf_with_default(server)
    ip = server.ip
    port = server_conf.get('rpc_port')
    service_str = f"{ip}:{port}"
    
    if not primary_cursor or not standby_cursor:
        stdio.error("Failed to get database cursors.")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # Check if the "Primary" is actually a real PRIMARY or just a higher-level STANDBY
    sql = "SELECT ROLE from oceanbase.__all_virtual_server_stat"
    res = primary_cursor.fetchone(sql, raise_exception=False)
    if not res:
        stdio.error("Failed to get cluster role for {}.".format(primary_deploy_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    
    primary_role = res['ROLE']
    
    if primary_role == 'PRIMARY':
        # Normal switchover: Primary -> Standby, Standby -> Primary
        stdio.verbose("Switching Primary cluster {} to Standby...".format(primary_deploy_name))
        try:
            primary_cursor.execute("ALTER SYSTEM SWITCHOVER TO STANDBY", raise_exception=True, stdio=stdio)
        except Exception as e:
            stdio.error("Failed to switchover Primary to Standby: {}".format(e))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        try:
            sql = "alter system set log_restore_source = '{}'".format(service_str)
            stdio.verbose("Setting LOG_RESTORE_SOURCE on old Primary...")
            primary_cursor.execute(sql, raise_exception=True, stdio=stdio)
        except Exception as e:
            stdio.warn("Failed to set LOG_RESTORE_SOURCE on old Primary: {}. Please set it manually.".format(e))

        stdio.verbose("Switching Standby cluster {} to Primary...".format(standby_deploy_name))
        try:
            standby_cursor.execute("ALTER SYSTEM SWITCHOVER TO PRIMARY", raise_exception=True, stdio=stdio)
        except Exception as e:
            stdio.error("Failed to switchover Standby to Primary: {}. Cluster might be in inconsistent state (Two Standbys).".format(e))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

        plugin_context.set_variable('start_obshell', True)
            
    elif primary_role == 'STANDBY':
        # Cascading switchover: Both are standbys, just swap their positions in the cascade
        # No role change needed, only need to update the log_restore_source of the old primary 
        # to point to the new primary. The new primarycwill point to the master.
        stdio.verbose("Both clusters are STANDBY (Cascading topology). Skipping role switchover commands.")
        try:
            sql = "alter system set log_restore_source = '{}'".format(service_str)
            stdio.verbose("Setting LOG_RESTORE_SOURCE on {} to point to {}...".format(primary_deploy_name, standby_deploy_name))
            primary_cursor.execute(sql, raise_exception=True, stdio=stdio)
        except Exception as e:
            stdio.warn("Failed to set LOG_RESTORE_SOURCE on {}: {}. Please set it manually.".format(primary_deploy_name, e))
        plugin_context.set_variable('seekdb_is_standby', True)
    else:
        stdio.error("Unknown cluster role {} for {}.".format(primary_role, primary_deploy_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    plugin_context.set_variable('switchover_success', True)
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
