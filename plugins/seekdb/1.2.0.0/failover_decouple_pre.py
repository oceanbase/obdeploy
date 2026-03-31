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

def failover_decouple_pre(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    option_type = kwargs.get('option_type')

    standby_cursor = cursors.get(standby_deploy_name)
    if not standby_cursor:
        stdio.error('Failed to connect standby deploy: {}.'.format(standby_deploy_name))
        return plugin_context.return_false()

    # 1. Check standby cluster existence and role
    stdio.start_loading('Check standby cluster role')
    sql = "select role from oceanbase.__all_virtual_server_stat"
    res = standby_cursor.fetchone(sql, raise_exception=False)
    if not res:
        stdio.error("Failed to get cluster role for {}.".format(standby_deploy_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    if res['role'] != 'STANDBY':
        stdio.error("Current cluster {} is not a STANDBY cluster (Role: {}). Cannot perform failover.".format(standby_deploy_name, res['role']))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    
    # 2. Check Primary Cluster Liveness
    # Try to find Primary Cluster info from config or LOG_RESTORE_SOURCE
    if option_type == 'failover':
        primary_deploy_name = None
        cluster_config = plugin_context.cluster_config
        primary_deploy_name = cluster_config.get_component_attr('_cluster_primary')
        
        primary_cursor = None
        if primary_deploy_name:
            primary_cursor = cursors.get(primary_deploy_name)

        # If we have a cursor from get_deployment_connections, it means Primary is reachable
        if primary_cursor:
            primary_cursor.execute("SELECT 1", raise_exception=False)
            stdio.error("Primary cluster {} is alive and reachable. Failover is not allowed. Please use Switchover instead.".format(primary_deploy_name))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
