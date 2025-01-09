# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


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