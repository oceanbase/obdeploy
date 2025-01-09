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
import copy

import _errno as err
from _types import Capacity
from tool import get_option


def tenant_check(plugin_context, **kwargs):
    critical = plugin_context.get_variable('check_fail')
    error = plugin_context.get_variable('error')
    cursor = plugin_context.get_variable('cursor') if plugin_context.get_variable('cursor') else kwargs.get('cursor')

    cluster_config = plugin_context.cluster_config
    options = plugin_context.options
    servers = cluster_config.servers
    stdio = plugin_context.stdio

    if not cluster_config.depends:
        if cursor:
            stdio.verbose('tenant check ')
            zone_obs_num = {}
            sql = "select zone, count(*) num from oceanbase.DBA_OB_SERVERS where status = 'active' group by zone"
            res = cursor.fetchall(sql)
            if res is False:
                return

            for row in res:
                zone_obs_num[str(row['zone'])] = row['num']
            zone_list = zone_obs_num.keys()
            if isinstance(zone_list, str):
                zones = zone_list.replace(';', ',').split(',')
            else:
                zones = zone_list
            zone_list = "('%s')" % "','".join(zones)

            min_unit_num = min(zone_obs_num.items(), key=lambda x: x[1])[1]
            unit_num = get_option(options, 'unit_num', min_unit_num)
            if unit_num > min_unit_num:
                error(servers[0], 'resource pool unit num is bigger than zone server count')
                return

            sql = "select count(*) num from oceanbase.DBA_OB_SERVERS where status = 'active' and start_service_time > 0"
            count = 30
            while count:
                num = cursor.fetchone(sql)
                if num is False:
                    return
                num = num['num']
                if num >= unit_num:
                    break
                count -= 1
                time.sleep(1)

            sql = "SELECT * FROM oceanbase.GV$OB_SERVERS where zone in %s" % zone_list
            servers_stats = cursor.fetchall(sql)
            if servers_stats is False:
                return
            cpu_available = servers_stats[0]['CPU_CAPACITY_MAX'] - servers_stats[0]['CPU_ASSIGNED_MAX']
            mem_available = servers_stats[0]['MEM_CAPACITY'] - servers_stats[0]['MEM_ASSIGNED']
            disk_available = servers_stats[0]['DATA_DISK_CAPACITY'] - servers_stats[0]['DATA_DISK_IN_USE']
            log_disk_available = servers_stats[0]['LOG_DISK_CAPACITY'] - servers_stats[0]['LOG_DISK_ASSIGNED']
            for servers_stat in servers_stats[1:]:
                cpu_available = min(servers_stat['CPU_CAPACITY_MAX'] - servers_stat['CPU_ASSIGNED_MAX'], cpu_available)
                mem_available = min(servers_stat['MEM_CAPACITY'] - servers_stat['MEM_ASSIGNED'], mem_available)
                disk_available = min(servers_stat['DATA_DISK_CAPACITY'] - servers_stat['DATA_DISK_IN_USE'], disk_available)
                log_disk_available = min(servers_stat['LOG_DISK_CAPACITY'] - servers_stat['LOG_DISK_ASSIGNED'], log_disk_available)

            global_conf_with_default = copy.deepcopy(cluster_config.get_global_conf_with_default())
            meta_db_memory_size = Capacity(global_conf_with_default['ocp_meta_tenant'].get('memory_size')).bytes
            monitor_db_memory_size = Capacity(global_conf_with_default['ocp_monitor_tenant'].get('memory_size', 0)).bytes
            meta_db_max_cpu = global_conf_with_default['ocp_meta_tenant'].get('max_cpu')
            monitor_db_max_cpu = global_conf_with_default['ocp_monitor_tenant'].get('max_cpu', 0)
            meta_db_log_disk_size = global_conf_with_default.get('ocp_meta_tenant_log_disk_size', 0)
            meta_db_log_disk_size = Capacity(meta_db_log_disk_size).bytes
            monitor_db_log_disk_size = global_conf_with_default.get('ocp_monitor_tenant_log_disk_size', 0)
            monitor_db_log_disk_size = Capacity(monitor_db_log_disk_size).bytes
            if meta_db_max_cpu and monitor_db_max_cpu:
                if int(meta_db_max_cpu) + int(monitor_db_max_cpu) > cpu_available:
                    critical(servers[0], 'tenant cpu', err.EC_OCP_SERVER_RESOURCE_NOT_ENOUGH.format(resource='cpu', avail=cpu_available, need=int(meta_db_max_cpu) + int(monitor_db_max_cpu)))
            if meta_db_memory_size and monitor_db_memory_size:
                if meta_db_memory_size + monitor_db_memory_size > mem_available:
                    critical(servers[0], 'tenant mem', err.EC_OCP_SERVER_EXIST_METADB_TENANT_MEMORY_NOT_ENOUGH.format(avail=Capacity(mem_available), need=Capacity(meta_db_memory_size + monitor_db_memory_size)), suggests=[err.SUG_OCP_SERVER_EXIST_METADB_TENANT_NOT_ENOUGH.format()])
            if meta_db_log_disk_size and monitor_db_log_disk_size:
                if meta_db_log_disk_size + monitor_db_log_disk_size > log_disk_available:
                    critical(servers[0], 'tenant clog', err.EC_OCP_SERVER_RESOURCE_NOT_ENOUGH.format(resource='log_disk_size', avail=Capacity(log_disk_available), need=Capacity(meta_db_log_disk_size + monitor_db_log_disk_size)))
    return plugin_context.return_true()