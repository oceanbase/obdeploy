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

def check_tls(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    server_config = cluster_config.get_server_conf_with_default(cluster_config.servers[0])
    
    if not server_config.get('enable_rpc_service'):
        return plugin_context.return_true()
        
    stdio.start_loading('Check RPC TLS status')
    
    # Get current cluster cursor
    connect_ret = plugin_context.get_return('connect')
    if connect_ret and connect_ret.get_return('cursor'):
        cursor = connect_ret.get_return('cursor')
    else:
        stdio.error('Failed to get current cluster database connection.')
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    current_name = cluster_config.deploy_name
    try:
        sql = "SELECT rpc_tls_enabled, rpc_cert_expire_time FROM oceanbase.__all_virtual_server_stat"
        res = cursor.fetchall(sql)
        if not res:
            stdio.error("No data found in oceanbase.__all_virtual_server_stat for cluster %s." % current_name)
            stdio.stop_loading('fail')
            return plugin_context.return_false()
            
        for row in res:
            tls_enabled = row.get('rpc_tls_enabled')
            expire_time = row.get('rpc_cert_expire_time')
            
            if str(tls_enabled) != '1':
                stdio.error("RPC TLS is not enabled (rpc_tls_enabled={}) on cluster {}.".format(tls_enabled, current_name))
                stdio.stop_loading('fail')
                return plugin_context.return_false()
                
            if expire_time is None or int(expire_time) <= 0:
                stdio.error("RPC certificate expire time is invalid (rpc_cert_expire_time={}) on cluster {}.".format(expire_time, current_name))
                stdio.stop_loading('fail')
                return plugin_context.return_false()
                
    except Exception as e:
        stdio.error("Failed to check TLS status on cluster {}: {}".format(current_name, e))
        stdio.stop_loading('fail')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
