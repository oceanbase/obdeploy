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

def switchover_check(plugin_context, cursors={}, cluster_configs={}, *args, **kwargs):
    stdio = plugin_context.stdio
    standby_deploy_name = plugin_context.cluster_config.deploy_name
    
    stdio.start_loading('Check switchover conditions')
    
    standby_cursor = cursors.get(standby_deploy_name)
    if not standby_cursor:
        stdio.error('Failed to connect standby deploy: {}.'.format(standby_deploy_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    sql = "SELECT ROLE from oceanbase.__all_virtual_server_stat"
    res = standby_cursor.fetchone(sql, raise_exception=False)
    if not res:
        stdio.error("Failed to get cluster role for {}.".format(standby_deploy_name))
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    if res['ROLE'] != 'STANDBY':
        stdio.error("Current cluster {} is not a STANDBY cluster (Role: {}). Please run switchover from the Standby cluster.".format(standby_deploy_name, res['ROLE']))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    primary_deploy_name = None
    
    cluster_config = plugin_context.cluster_config
    primary_deploy_name = cluster_config.get_component_attr('_cluster_primary')

    # Check LOG_RESTORE_SOURCE
    if not primary_deploy_name:
        sql = "select log_restore_source from oceanbase.__all_virtual_server_stat"
        res = standby_cursor.fetchone(sql, raise_exception=False)
        if res and res.get('log_restore_source'):
            log_restore_source = res.get('log_restore_source')
            parts = log_restore_source.split(':')
            ip = parts[0].strip()
            port = parts[1].strip()
            for name, config in cluster_configs.items():
                if name == standby_deploy_name:
                    continue
                server = config.servers[0]
                if server.ip == ip:
                    server_conf = cluster_config.get_server_conf_with_default(server)
                    if str(server_conf.get('rpc_port')) == port:
                        primary_deploy_name = name
                        break

    if not primary_deploy_name:
        stdio.error("not found primary cluster")
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    plugin_context.set_variable('primary_deploy_name', primary_deploy_name)
    plugin_context.set_variable('standby_deploy_name', standby_deploy_name)
    
    stdio.verbose("Switchover check passed. Primary: {}, Standby: {}".format(primary_deploy_name, standby_deploy_name))
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
