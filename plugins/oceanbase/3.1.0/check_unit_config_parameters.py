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


def check_unit_config_parameters(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        if key in kwargs:
            return kwargs[key]
        value = getattr(plugin_context.options, key, default)
        if not value:
            value = default
        return value

    def get_parsed_option(key, default=''):
        value = get_option(key=key, default=default)
        try:
            parsed_value = Capacity(value).bytes
        except:
            stdio.exception("")
            raise Exception("Invalid option {}: {}".format(key, value))
        return parsed_value

    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')

    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('cursor')
    zone_list = get_option('zone_list', set())
    zone_obs_num = {}
    sql = "select zone, count(*) num from oceanbase.__all_server where status = 'active' group by zone"
    res = cursor.fetchall(sql)
    if res is False:
        stdio.stop_loading('fail')
        return plugin_context.return_false()
    for row in res:
        zone_obs_num[str(row['zone'])] = row['num']
    if not zone_list:
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
    cpu_available = servers_stats[0]['CPU_CAPACITY_MAX'] - servers_stats[0]['CPU_ASSIGNED_MAX']
    mem_available = servers_stats[0]['MEM_CAPACITY'] - servers_stats[0]['MEM_ASSIGNED']
    disk_available = servers_stats[0]['DATA_DISK_CAPACITY'] - servers_stats[0]['DATA_DISK_IN_USE']
    log_disk_available = servers_stats[0]['LOG_DISK_CAPACITY'] - servers_stats[0]['LOG_DISK_ASSIGNED']
    for servers_stat in servers_stats[1:]:
        cpu_available = min(servers_stat['CPU_CAPACITY_MAX'] - servers_stat['CPU_ASSIGNED_MAX'], cpu_available)
        mem_available = min(servers_stat['MEM_CAPACITY'] - servers_stat['MEM_ASSIGNED'], mem_available)
        disk_available = min(servers_stat['DATA_DISK_CAPACITY'] - servers_stat['DATA_DISK_IN_USE'], disk_available)
        log_disk_available = min(servers_stat['LOG_DISK_CAPACITY'] - servers_stat['LOG_DISK_ASSIGNED'], log_disk_available)

    MIN_CPU = 1
    MIN_MEMORY = 1073741824
    MIN_LOG_DISK_SIZE = 2147483648
    MIN_IOPS = 1024

    if cpu_available < MIN_CPU:
        error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list,
                                                                                     available=cpu_available,
                                                                                     need=MIN_CPU))
        return plugin_context.return_false()
    if mem_available < MIN_MEMORY:
        error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list,
                                                                                        available=Capacity(
                                                                                            mem_available),
                                                                                        need=Capacity(MIN_MEMORY)))
        return plugin_context.return_false()
    if log_disk_available < MIN_LOG_DISK_SIZE:
        error('{zone} not enough log_disk. (Available: {available}, Need: {need})'.format(zone=zone_list,
                                                                                          available=Capacity(
                                                                                              log_disk_available),
                                                                                          need=Capacity(
                                                                                              MIN_LOG_DISK_SIZE)))
        return plugin_context.return_false()

    max_cpu = get_option('max_cpu', cpu_available)
    min_cpu = get_option('min_cpu', max_cpu)
    if cpu_available < max_cpu:
        error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list,
                                                                                     available=cpu_available,
                                                                                     need=max_cpu))
        return plugin_context.return_false()
    if max_cpu < min_cpu:
        error('min_cpu must less then max_cpu')
        return plugin_context.return_false()

    # memory options
    memory_size = get_option('memory_size')
    if memory_size:
        memory_size = Capacity(memory_size).bytes
    else:
        memory_size = mem_available
    log_disk_size = None
    try:
        log_disk_size = get_parsed_option('log_disk_size')
    except Exception as e:
        error(e)
    if mem_available < memory_size:
        error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list,
                                                                                        available=Capacity(
                                                                                            mem_available),
                                                                                        need=Capacity(memory_size)))
        return plugin_context.return_false()

    # log disk size options
    if log_disk_size is not None and log_disk_available < log_disk_size:
        error('{zone} not enough log_disk. (Available: {available}, Need: {need})'.format(zone=zone_list,
                                                                                          available=Capacity(
                                                                                              log_disk_available),
                                                                                          need=Capacity(log_disk_size)))
        return plugin_context.return_false()

    # iops options
    max_iops = get_option('max_iops', MIN_IOPS)
    min_iops = get_option('min_iops', max_iops)
    if max_iops is not None and max_iops < MIN_IOPS:
        error('max_iops must greater than %d' % MIN_IOPS)
        return plugin_context.return_false()
    if max_iops is not None and min_iops is not None and max_iops < min_iops:
        error('min_iops must less then max_iops')
        return plugin_context.return_false()

    plugin_context.set_variable('error', error)
    plugin_context.set_variable('max_cpu', max_cpu)
    plugin_context.set_variable('memory_size', str(Capacity(memory_size)))
    return plugin_context.return_true()
