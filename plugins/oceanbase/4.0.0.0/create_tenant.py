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


import re
import time

from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN


def parse_size(size):
    _bytes = 0
    if isinstance(size, str):
        size = size.strip()
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'^([1-9][0-9]*)\s*([B,K,M,G,T])$', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G', 'T', 'P']
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
    else:
        div = 1024
        format = '%d%s'
    while idx < 5 and size >= 1024:
        size /= 1024.0
        idx += 1
    return format % (size, units[idx])


def create_tenant(plugin_context, cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value

    def get_parsed_option(key, default=''):
        value = get_option(key=key, default=default)
        if value is None:
            return value
        try:
            parsed_value = parse_size(value)
        except:
            stdio.exception("")
            raise Exception("Invalid option {}: {}".format(key, value))
        return parsed_value

    def error(*arg, **kwargs):
        stdio.error(*arg, **kwargs)
        stdio.stop_loading('fail')
    def exception(*arg, **kwargs):
        stdio.exception(*arg, **kwargs)
        stdio.stop_loading('fail')
        
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    options = plugin_context.options
    
    mode = get_option('mode', 'mysql').lower()
    if not mode in ['mysql', 'oracle']:
        error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
        return 

    # options not support
    deserted_options = ('max_session_num', 'max_memory', 'min_memory', 'max_disk_size')
    for opt in deserted_options:
        if get_option(opt, None) is not None:
            stdio.warn("option {} is no longer supported".format(opt))

    name = get_option('tenant_name', 'test')
    unit_name = '%s_unit' % name
    sql = 'select * from oceanbase.DBA_OB_UNIT_CONFIGS order by name'
    try:
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
    except:
        exception('execute sql exception: %s' % sql)
        return

    res = cursor.fetchall()
    for row in res:
        if str(row['NAME']) == unit_name:
            unit_name += '1'

    pool_name = '%s_pool' % name
    
    stdio.start_loading('Create tenant %s' % name)
    sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    try:
        stdio.verbose('execute sql: %s' % (sql % name))
        cursor.execute(sql, [name])
        if cursor.fetchone():
            error('Tenant %s already exists' % name)
            return
    except:
        exception('execute sql exception: %s' % (sql % name))
        return

    zone_list = get_option('zone_list', set())
    zone_obs_num = {}
    sql = "select zone, count(*) num from oceanbase.__all_server where status = 'active' group by zone"
    try:
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
        res = cursor.fetchall()
        for row in res:
            zone_obs_num[str(row['zone'])] = row['num']
    except:
        exception('execute sql exception: %s' % sql)
        return
    if not zone_list:
        zone_list = zone_obs_num.keys()
    if isinstance(zone_list, str):
        zones = zone_list.replace(';', ',').split(',')
    else:
        zones = zone_list
    zone_list = "('%s')" % "','".join(zones)

    min_unit_num = min(zone_obs_num.items(),key=lambda x: x[1])[1]
    unit_num = get_option('unit_num', min_unit_num)
    if unit_num > min_unit_num:
        return error('resource pool unit num is bigger than zone server count')
    
    sql = "select count(*) num from oceanbase.__all_server where status = 'active' and start_service_time > 0"
    try:
        count = 30
        while count:
            stdio.verbose('execute sql: %s' % sql)
            cursor.execute(sql)
            num = cursor.fetchone()['num']
            if num >= unit_num:
                break
            count -= 1
            time.sleep(1)
        if count == 0:
            stdio.error(EC_OBSERVER_CAN_NOT_MIGRATE_IN)
            return
    except:
        exception('execute sql exception: %s' % sql)
        return

    sql = "SELECT * FROM oceanbase.GV$OB_SERVERS where zone in %s"
    try:
        sql = sql % zone_list
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
    except:
        exception('execute sql exception: %s' % sql)
        return
    servers_stats = cursor.fetchall()
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
        return error('%s: resource not enough: cpu count less than %s' % (zone_list, MIN_CPU))
    if mem_available < MIN_MEMORY:
        return error('%s: resource not enough: memory less than %s' % (zone_list, format_size(MIN_MEMORY)))
    if log_disk_available < MIN_LOG_DISK_SIZE:
        return error('%s: resource not enough: log disk size less than %s' % (zone_list, format_size(MIN_MEMORY)))

    # cpu options
    max_cpu = get_option('max_cpu', cpu_available)
    min_cpu = get_option('min_cpu', max_cpu)
    if cpu_available < max_cpu:
        return error('resource not enough: cpu (Avail: %s, Need: %s)' % (cpu_available, max_cpu))
    if max_cpu < min_cpu:
        return error('min_cpu must less then max_cpu')

    # memory options
    memory_size = get_parsed_option('memory_size', None)
    log_disk_size = get_parsed_option('log_disk_size', None)

    if memory_size is None:
        memory_size = mem_available
        if log_disk_size is None:
            log_disk_size = log_disk_available

    if mem_available < memory_size:
        return error('resource not enough: memory (Avail: %s, Need: %s)' % (format_size(mem_available), format_size(memory_size)))

    # log disk size options
    if log_disk_size is not None and log_disk_available < log_disk_size:
        return error('resource not enough: log disk space (Avail: %s, Need: %s)' % (format_size(disk_available), format_size(log_disk_size)))

    # iops options
    max_iops = get_option('max_iops', None)
    min_iops = get_option('min_iops', None)
    iops_weight = get_option('iops_weight', None)
    if max_iops is not None and max_iops < MIN_IOPS:
        return error('max_iops must greater than %d' % MIN_IOPS)
    if max_iops is not None and min_iops is not None and max_iops < min_iops:
        return error('min_iops must less then max_iops')

    zone_num = len(zones)
    charset = get_option('charset', '')
    collate = get_option('collate', '')
    replica_num = get_option('replica_num', zone_num)
    logonly_replica_num = get_option('logonly_replica_num', 0)
    tablegroup = get_option('tablegroup', '')
    primary_zone = get_option('primary_zone', 'RANDOM')
    locality = get_option('locality', '')
    variables = get_option('variables', '')

    if replica_num == 0:
        replica_num = zone_num
    elif replica_num > zone_num:
        return error('replica_num cannot be greater than zone num (%s)' % zone_num)
    if not primary_zone:
        primary_zone = 'RANDOM'
    if logonly_replica_num > replica_num:
        return error('logonly_replica_num cannot be greater than replica_num (%s)' % replica_num)
    
    # create resource unit
    sql = "create resource unit %s max_cpu %.1f, memory_size %d" % (unit_name, max_cpu, memory_size)
    if min_cpu is not None:
        sql += ', min_cpu %.1f' % min_cpu
    if max_iops is not None:
        sql += ', max_iops %d' % max_iops
    if min_iops is not None:
        sql += ', min_iops %d' % min_iops
    if iops_weight is not None:
        sql += ', iops_weight %d' % iops_weight
    if log_disk_size is not None:
        sql += ', log_disk_size %d' % log_disk_size
    try:
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
    except:
        exception('faild to crate unit, execute sql exception: %s' % sql)
        return

    # create resource pool
    sql = "create resource pool %s unit='%s', unit_num=%d, zone_list=%s" % (pool_name, unit_name, unit_num, zone_list)
    try:
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
    except:
        exception('failed to create pool, execute sql exception: %s' % sql)
        return

    # create tenant
    sql = "create tenant %s replica_num=%d,zone_list=%s,primary_zone='%s',resource_pool_list=('%s')"
    sql = sql % (name, replica_num, zone_list, primary_zone, pool_name)
    if charset:
        sql += ", charset = '%s'" % charset
    if collate:
        sql += ", collate = '%s'" % collate
    if logonly_replica_num:
        sql += ", logonly_replica_num = %d" % logonly_replica_num
    if tablegroup:
        sql += ", default tablegroup ='%s'" % tablegroup
    if locality:
        sql += ", locality = '%s'" % locality

    set_mode = "ob_compatibility_mode = '%s'" % mode
    if variables:
        sql += "set %s, %s" % (variables, set_mode)
    else:
        sql += "set %s" % set_mode
    try:
        stdio.verbose('execute sql: %s' % sql)
        cursor.execute(sql)
    except:
        exception('faild to crate tenant, execute sql exception: %s' % sql)
        return
        
    stdio.stop_loading('succeed')
    return plugin_context.return_true()