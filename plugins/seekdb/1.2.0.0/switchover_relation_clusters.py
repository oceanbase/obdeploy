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

def switchover_relation_clusters(plugin_context, cluster_configs={}, cursors={}, *args, **kwargs):
    stdio = plugin_context.stdio
    deploy_manager = kwargs.get('deploy_manager')
    
    stdio.start_loading('Update cluster relation configurations')
    
    # Old Primary (New Standby)
    primary_deploy_name = plugin_context.get_variable('primary_deploy_name')
    # Old Standby (New Primary)
    standby_deploy_name = plugin_context.get_variable('standby_deploy_name')
    
    if not primary_deploy_name or not standby_deploy_name:
        stdio.error("Missing deploy names for relation update.")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # Get deployment configs
    old_primary_deploy = deploy_manager.get_deploy_config(primary_deploy_name)
    old_standby_deploy = deploy_manager.get_deploy_config(standby_deploy_name)
    
    if not old_primary_deploy or not old_standby_deploy:
        stdio.error("Failed to load deployment configurations.")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # Get SeekDB components
    old_primary_conf = cluster_configs.get(primary_deploy_name)
    old_standby_conf = cluster_configs.get(standby_deploy_name)
    
    if not old_primary_conf or not old_standby_conf:
        stdio.error("Failed to get seekdb component configurations.")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    # Prepare connection strings and passwords
    new_primary_cursor = cursors.get(standby_deploy_name) # Cursor to (New Primary)
    new_standby_cursor = cursors.get(primary_deploy_name) # Cursor to (New Standby)

    if not new_primary_cursor or not new_standby_cursor:
        stdio.warn("Missing cursors for main clusters. Cascading updates might fail.")
    
    new_primary_server = old_standby_conf.servers[0]
    new_primary_server_conf = old_standby_conf.get_server_conf_with_default(new_primary_server)
    new_primary_service = "%s:%s" % (new_primary_server.ip, new_primary_server_conf.get('rpc_port'))

    new_standby_server = old_primary_conf.servers[0]
    new_standby_server_conf = old_primary_conf.get_server_conf_with_default(new_standby_server)
    new_standby_service = "%s:%s" % (new_standby_server.ip, new_standby_server_conf.get('rpc_port'))
    
    # Initialize new standby lists
    new_standby_standbys = [] 
    new_primary_standbys = [primary_deploy_name] 

    # Get the primary of the old primary
    old_primary_s_primary = old_primary_conf.get_component_attr('_cluster_primary')
    for name, conf in cluster_configs.items():
        if name == primary_deploy_name or name == standby_deploy_name:
            continue

        cursor = cursors.get(name)
        current_primary = conf.get_component_attr('_cluster_primary')

        if current_primary == primary_deploy_name:
            # Sibling standby of the one we're switching (star: stand01 and stand02 both under master).
            # After switchover, make it direct standby of the new primary to keep star shape.
            new_primary_standbys.append(name)
            conf.update_component_attr('_cluster_primary', standby_deploy_name, save=True)
            if cursor and new_primary_service:
                sql = "alter system set log_restore_source = '{}'".format(new_primary_service)
                try:
                    cursor.execute(sql, raise_exception=True)
                    stdio.verbose("Updated LOG_RESTORE_SOURCE for {} to point to New Primary {}.".format(name, standby_deploy_name))
                except Exception as e:
                    stdio.error("Failed to update LOG_RESTORE_SOURCE for {}: {}".format(name, e))

        elif current_primary == standby_deploy_name:
            # Cluster was under the old standby
            new_standby_standbys.append(name)
            conf.update_component_attr('_cluster_primary', primary_deploy_name, save=True)
            if cursor and new_standby_service:
                sql = "alter system set log_restore_source = '{}'".format(new_standby_service)
                try:
                    cursor.execute(sql, raise_exception=True)
                    stdio.verbose("Updated LOG_RESTORE_SOURCE for {} to point to New Standby {}.".format(name, primary_deploy_name))
                except Exception as e:
                    stdio.error("Failed to update LOG_RESTORE_SOURCE for {}: {}".format(name, e))

        # If this is the top-level primary (old_primary_s_primary), update its standby list
        if name == old_primary_s_primary:
            master_standbys = conf.get_component_attr('_cluster_standby_relation') or []
            if primary_deploy_name in master_standbys:
                master_standbys.remove(primary_deploy_name)
            if standby_deploy_name not in master_standbys:
                master_standbys.append(standby_deploy_name)
            conf.update_component_attr('_cluster_standby_relation', master_standbys, save=True)

    old_primary_conf.update_component_attr('_cluster_primary', standby_deploy_name, save=True)
    old_primary_conf.update_component_attr('_cluster_standby_relation', new_standby_standbys, save=True)

    old_standby_conf.update_component_attr('_cluster_primary', old_primary_s_primary, save=True)
    old_standby_conf.update_component_attr('_cluster_standby_relation', new_primary_standbys, save=True)
    
    # If the new primary is actually a standby of a higher master, update its LOG_RESTORE_SOURCE
    if old_primary_s_primary:
        master_conf = cluster_configs.get(old_primary_s_primary)
        if master_conf:
            master_server = master_conf.servers[0]
            master_server_conf = master_conf.get_server_conf_with_default(master_server)
            master_service = "%s:%s" % (master_server.ip, master_server_conf.get('rpc_port'))
            if new_primary_cursor and master_service:
                sql = "alter system set log_restore_source = '{}'".format(master_service)
                try:
                    new_primary_cursor.execute(sql, raise_exception=True)
                    stdio.verbose("Updated LOG_RESTORE_SOURCE for {} to point to Master {}.".format(standby_deploy_name, old_primary_s_primary))
                except Exception as e:
                    stdio.warn("Failed to update LOG_RESTORE_SOURCE for {}: {}".format(standby_deploy_name, e))

    stdio.verbose("Updated cluster relations and LOG_RESTORE_SOURCE for all clusters.")
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
