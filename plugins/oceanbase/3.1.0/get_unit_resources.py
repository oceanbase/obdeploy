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

from _types import Capacity


def get_unit_resources(plugin_context, *args, **kwargs):

    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')

    stdio = plugin_context.stdio
    global_conf = plugin_context.cluster_config.get_global_conf()
    cursor = plugin_context.get_return('connect').get_return('cursor')

    zone_obs_num = {}
    sql = "select zone, count(*) num from oceanbase.__all_server where status = 'active' group by zone"
    res = cursor.fetchall(sql)
    if res is False:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    for row in res:
        zone_obs_num[str(row['zone'])] = row['num']

    zone_list = zone_obs_num.keys()
    if isinstance(zone_list, str):
        zones = zone_list.replace(';', ',').split(',')
    else:
        zones = zone_list
    zone_list = "('%s')" % "','".join(zones)
    sql = "SELECT * FROM oceanbase.GV$OB_SERVERS where zone in %s" % zone_list
    servers_stats = cursor.fetchall(sql)
    if servers_stats is False:
        error()
        return
    max_cpu = servers_stats[0]['CPU_CAPACITY_MAX'] - servers_stats[0]['CPU_ASSIGNED_MAX']
    max_memory = servers_stats[0]['MEM_CAPACITY'] - servers_stats[0]['MEM_ASSIGNED']
    max_log_disk = servers_stats[0]['LOG_DISK_CAPACITY'] - servers_stats[0]['LOG_DISK_ASSIGNED']
    for servers_stat in servers_stats[1:]:
        max_cpu = min(servers_stat['CPU_CAPACITY_MAX'] - servers_stat['CPU_ASSIGNED_MAX'], max_cpu)
        max_memory = min(servers_stat['MEM_CAPACITY'] - servers_stat['MEM_ASSIGNED'], max_memory)
        max_log_disk = min(servers_stat['LOG_DISK_CAPACITY'] - servers_stat['LOG_DISK_ASSIGNED'], max_log_disk)

    MIN_CPU = 1
    MIN_MEMORY = global_conf.get('__min_full_resource_pool_memory', 2 << 30)
    MIN_LOG_DISK_SIZE = 2147483648
    resource = {
        "cpu_capacity": {
            "max": max_cpu,
            "min": MIN_CPU,
        },
        "mem_capacity": {
            "max": str(Capacity(max_memory)),
            "min": str(Capacity(MIN_MEMORY)),
        },
        "log_disk_capacity": {
            "max": str(Capacity(max_log_disk)),
            "min": str(Capacity(MIN_MEMORY*3)),
        }
    }
    return plugin_context.return_true(unit_resource=resource)
