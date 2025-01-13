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

import time


def active_check(plugin_context,  *args, **kwargs):
    
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    restart_manager = plugin_context.get_variable('restart_manager')

    stdio.start_loading('Observer active check')
    if not restart_manager.connect():
        stdio.stop_loading('stop_loading', 'fail')
        return plugin_context.return_false()
    while True:
        for server in cluster_config.servers:
            config = cluster_config.get_server_conf(server)
            sql = '''
            select count(*) as cnt from oceanbase.__all_tenant as a left join (
                select tenant_id, refreshed_schema_version 
                from oceanbase.__all_virtual_server_schema_info 
                where svr_ip = %s and svr_port = %s and refreshed_schema_version > 1
                ) as b on a.tenant_id = b.tenant_id 
            where b.tenant_id is null'''
            if restart_manager.execute_sql(sql, args=(server.ip, config['rpc_port']), error=False).get('cnt'):
                break
        else:
            break
        time.sleep(3)

    while restart_manager.execute_sql(
            "select * from oceanbase.__all_virtual_clog_stat where table_id = 1099511627777 and status != 'ACTIVE'",
            error=False):
        time.sleep(3)
    stdio.stop_loading('stop_loading', 'success')
    return plugin_context.return_true()