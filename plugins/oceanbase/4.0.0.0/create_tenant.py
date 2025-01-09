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
from collections import defaultdict

from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN
from _types import Capacity

tenant_cursor_cache = defaultdict(dict)


def create_tenant(plugin_context, create_tenant_options=[], cursor=None, scale_out_component='', *args, **kwargs):
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
            parsed_value = Capacity(value).bytes
        except:
            stdio.exception("")
            raise Exception("Invalid option {}: {}".format(key, value))
        return parsed_value

    def error(msg='', *arg, **kwargs):
        msg and stdio.error(msg, *arg, **kwargs)
        stdio.stop_loading('fail')

    stdio = plugin_context.stdio
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    if scale_out_component in ['ocp-server-ce', 'ocp-express']:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    for options in multi_options:
        create_if_not_exists = get_option('create_if_not_exists', False)
        cursor = plugin_context.get_return('connect', spacename='oceanbase-ce').get_return('cursor') if not cursor else cursor
        global tenant_cursor
        tenant_cursor = None

        mode = get_option('mode', 'mysql').lower()
        if not mode in ['mysql', 'oracle']:
            error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
            return plugin_context.return_false()

        # options not support
        deserted_options = ('max_session_num', 'max_memory', 'min_memory', 'max_disk_size')
        for opt in deserted_options:
            if get_option(opt, None) is not None:
                stdio.warn("option {} is no longer supported".format(opt))

        name = get_option('tenant_name', 'test')
        unit_name = '%s_unit' % name
        sql = 'select * from oceanbase.DBA_OB_UNIT_CONFIGS order by name'
        res = cursor.fetchall(sql, raise_exception=True)
        if res is False:
            return
        for row in res:
            if str(row['NAME']) == unit_name:
                unit_name += '1'

        pool_name = '%s_pool' % name

        sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
        tenant_exists = False
        plugin_context.set_variable('tenant_exists', tenant_exists)
        res = cursor.fetchone(sql, [name])
        if res:
            plugin_context.set_variable('tenant_exists', True)
            if create_if_not_exists:
                continue
            else:
                error('Tenant %s already exists' % name)
                return
        elif res is False:
            return

        if not tenant_exists:
            stdio.start_loading('Create tenant %s' % name)
            zone_list = get_option('zone_list', set())
            zone_obs_num = {}
            sql = "select zone, count(*) num from oceanbase.__all_server where status = 'active' group by zone"
            res = cursor.fetchall(sql)
            if res is False:
                error()
                return

            for row in res:
                zone_obs_num[str(row['zone'])] = row['num']

            if not zone_list:
                zone_list = zone_obs_num.keys()
            if isinstance(zone_list, str):
                zones = zone_list.replace(';', ',').split(',')
            else:
                zones = zone_list
            zone_list = "('%s')" % "','".join(zones)

            min_unit_num = min(zone_obs_num.items(), key=lambda x: x[1])[1]
            unit_num = get_option('unit_num', min_unit_num)
            if unit_num > min_unit_num:
                error('resource pool unit num is bigger than zone server count')
                return plugin_context.return_false()

            sql = "select count(*) num from oceanbase.__all_server where status = 'active' and start_service_time > 0"
            count = 30
            while count:
                num = cursor.fetchone(sql)
                if num is False:
                    error()
                    return
                num = num['num']
                if num >= unit_num:
                    break
                count -= 1
                time.sleep(1)
            if count == 0:
                stdio.error(EC_OBSERVER_CAN_NOT_MIGRATE_IN)
                return

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
                error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list, available=cpu_available, need=MIN_CPU))
                return plugin_context.return_false()
            if mem_available < MIN_MEMORY:
                error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(mem_available), need=Capacity(MIN_MEMORY)))
                return plugin_context.return_false()
            if log_disk_available < MIN_LOG_DISK_SIZE:
                error('{zone} not enough log_disk. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(log_disk_available), need=Capacity(MIN_LOG_DISK_SIZE)))
                return plugin_context.return_false()

            # cpu options
            max_cpu = get_option('max_cpu', cpu_available)
            min_cpu = get_option('min_cpu', max_cpu)
            if cpu_available < max_cpu:
                error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list, available=cpu_available, need=max_cpu))
                return plugin_context.return_false()
            if max_cpu < min_cpu:
                error('min_cpu must less then max_cpu')
                return plugin_context.return_false()

            # memory options
            memory_size = get_parsed_option('memory_size', None)
            log_disk_size = get_parsed_option('log_disk_size', None)

            if memory_size is None:
                memory_size = mem_available
                if log_disk_size is None:
                    log_disk_size = log_disk_available

            if mem_available < memory_size:
                error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(mem_available), need=Capacity(memory_size)))
                return plugin_context.return_false()

            # log disk size options
            if log_disk_size is not None and log_disk_available < log_disk_size:
                error('{zone} not enough log_disk. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(log_disk_available), need=Capacity(log_disk_size)))
                return plugin_context.return_false()

            # iops options
            max_iops = get_option('max_iops', None)
            min_iops = get_option('min_iops', None)
            iops_weight = get_option('iops_weight', None)
            if max_iops is not None and max_iops < MIN_IOPS:
                error('max_iops must greater than %d' % MIN_IOPS)
                return plugin_context.return_false()
            if max_iops is not None and min_iops is not None and max_iops < min_iops:
                error('min_iops must less then max_iops')
                return plugin_context.return_false()

            zone_num = len(zones)
            charset = get_option('charset', '')
            collate = get_option('collate', '')
            replica_num = get_option('replica_num', zone_num)
            logonly_replica_num = get_option('logonly_replica_num', 0)
            tablegroup = get_option('tablegroup', '')
            primary_zone = get_option('primary_zone', 'RANDOM')
            locality = get_option('locality', '')
            variables = get_option('variables', "ob_tcp_invited_nodes='%'")

            if replica_num == 0:
                replica_num = zone_num
            elif replica_num > zone_num:
                error('replica_num cannot be greater than zone num (%s)' % zone_num)
                return plugin_context.return_false()
            if not primary_zone:
                primary_zone = 'RANDOM'
            if logonly_replica_num > replica_num:
                error('logonly_replica_num cannot be greater than replica_num (%s)' % replica_num)
                return plugin_context.return_false()

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

            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                error('create resource unit failed')
                return plugin_context.return_false()

            # create resource pool
            sql = "create resource pool %s unit='%s', unit_num=%d, zone_list=%s" % (pool_name, unit_name, unit_num, zone_list)
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                error('create resource pool failed')
                return plugin_context.return_false()

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
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                error('create tenant failed')
                return plugin_context.return_false()
        stdio.stop_loading('succeed')
    plugin_context.set_variable('error', error)
    return plugin_context.return_true()
