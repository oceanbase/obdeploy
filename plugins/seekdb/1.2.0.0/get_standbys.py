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

def get_ip_list(cluster_config):
    ip_list = []
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        ip_list.append("{}:{}".format(server.ip, server_config.get('rpc_port')))
    ip_list.sort()
    return ip_list


def get_standbys(plugin_context, relation_deploy_names=[], cursors={}, cluster_configs={}, skip_no_primary_cursor=False, *args, **kwargs):
    stdio = plugin_context.stdio
    primary_deploy_name = plugin_context.cluster_config.deploy_name
    
    stdio.start_loading('Get standbys info')
    
    if skip_no_primary_cursor and (not cursors or not cursors.get(primary_deploy_name)):
        stdio.verbose('Connect to {} failed. skip get standby'.format(primary_deploy_name))
        plugin_context.set_variable('standby_clusters', [])
        plugin_context.set_variable('no_primary_cursor', True)
        stdio.stop_loading('succeed')
        return plugin_context.return_true(standby_clusters=[])

    if not cursors:
        stdio.error('Connect to SeekDB failed.')
        stdio.stop_loading('fail')
        return

    standby_clusters = []
    
    # 1. Get Primary IP List
    if primary_deploy_name not in cluster_configs:
        stdio.error("Configuration for {} not found".format(primary_deploy_name))
        stdio.stop_loading('fail')
        return

    primary_cluster_config = cluster_configs[primary_deploy_name]
    primary_ip_list = get_ip_list(primary_cluster_config)
    
    if not primary_ip_list:
        stdio.verbose("Could not retrieve IP list for primary {}".format(primary_deploy_name))
    
    # 2. Iterate Potential Standbys
    # In SeekDB context, relation_deploy_names contains all related clusters
    
    for relation_name in relation_deploy_names:
        if relation_name == primary_deploy_name:
            continue
        
        cursor = cursors.get(relation_name)
        if not cursor:
            stdio.verbose("Connect to {} failed.".format(relation_name))
            continue
            
        # Check Role
        sql = "SELECT ROLE from oceanbase.__all_virtual_server_stat"
        res = cursor.fetchone(sql, raise_exception=False)
        if not res:
            continue
        
        if res['ROLE'] != 'STANDBY':
            continue
            
        # Check Restore Source
        sql = "select log_restore_source from oceanbase.__all_virtual_server_stat"
        res = cursor.fetchone(sql, raise_exception=False)
        
        if not res or not res.get('log_restore_source'):
            continue
            
        sources = res.get('log_restore_source')
        
        if primary_ip_list:
            if sources.strip() in primary_ip_list:
                standby_clusters.append(relation_name)  

    plugin_context.set_variable('standby_clusters', standby_clusters)
    stdio.stop_loading('succeed')
    return plugin_context.return_true(standby_clusters=standby_clusters)
