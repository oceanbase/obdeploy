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

from requests import options

from tool import get_option, set_plugin_context_variables
from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN
from _types import Capacity

def create_standby_resource(plugin_context, config_encrypted, cursor=None, create_tenant_options=[], relation_tenants={}, cluster_configs={}, primary_tenant_info={}, standbyro_password='', *args, **kwargs):
    def get_parsed_option(key, default=''):
        value = get_option(options, key=key, default=default)
        if value is None:
            return value
        try:
            parsed_value = Capacity(value).bytes
        except:
            stdio.exception("")
            raise Exception("Invalid option {}: {}".format(key, value))
        return parsed_value

    stdio = plugin_context.stdio
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    error = plugin_context.get_variable('error')
    variables_dict = {}

    for options in multi_options:
        create_if_not_exists = get_option(options, 'create_if_not_exists', False)
        standby_deploy_name = plugin_context.cluster_config.deploy_name
        cursor = plugin_context.get_return('connect').get_return('cursor') if not cursor else cursor
        cursor = cursor if cursor else plugin_context.get_variable('cursors').get(standby_deploy_name)
        global tenant_cursor
        tenant_cursor = None
        zone_list = get_option(options, 'zone_list', set())
        locality = get_option(options, 'locality', '')
        primary_zone = get_option(options, 'primary_zone', 'RANDOM')

        if primary_tenant_info:
            primary_deploy_name = primary_tenant_info.get('primary_deploy_name')
            primary_tenant = primary_tenant_info.get('primary_tenant')
            primary_cursor = plugin_context.get_variable('cursors').get(primary_deploy_name)
            primary_memory_size = primary_tenant_info['memory_size']
            primary_log_disk_size = primary_tenant_info['log_disk_size']
            primary_params = ['max_cpu', 'min_cpu', 'unit_num', 'memory_size', 'log_disk_size', 'max_iops', 'min_iops', 'iops_weight']
            for param in primary_params:
                if get_option(options, param, None) is None and param in primary_tenant_info:
                    setattr(options, param, primary_tenant_info[param])

            # options not support
            deserted_options = ('max_session_num', 'max_memory', 'min_memory', 'max_disk_size')
            for opt in deserted_options:
                if get_option(options, opt, None) is not None:
                    stdio.warn("option {} is no longer supported".format(opt))

            name = get_option(options, 'tenant_name', primary_tenant)
            unit_name = '%s_unit' % name

            sql = 'select * from oceanbase.DBA_OB_UNIT_CONFIGS where name like "{}%" order by unit_config_id desc limit 1'.format(unit_name)
            res = cursor.fetchone(sql)
            if res is False:
                return
            if res:
                unit_name += '{}'.format(int(res['UNIT_CONFIG_ID']) + 1)

            pool_name = '%s_pool' % name

            sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
            tenant_exists = False
            res = cursor.fetchone(sql, (name, ))
            if res:
                if create_if_not_exists:
                    continue
                else:
                    error('Tenant %s already exists' % name)
                    return
            elif res is False:
                return

            if not tenant_exists:
                stdio.start_loading('Create tenant %s resource' % name)
                zone_list = get_option(options, 'zone_list', set())
                zone_obs_num = {}
                sql = "select zone, count(*) num from oceanbase.__all_server where status = 'active' group by zone"
                res = cursor.fetchall(sql)
                if res is False:
                    error()
                    return

                for row in res:
                    zone_obs_num[str(row['zone'])] = row['num']
                if not zone_list:
                    zones = zone_obs_num.keys()
                else:
                    zones = zone_list
                zone_list = "('%s')" % "','".join(zones)

                min_unit_num = min(zone_obs_num.items(), key=lambda x: x[1])[1]
                unit_num = get_option(options, 'unit_num', min_unit_num)
                if unit_num > min_unit_num:
                    return error('resource pool unit num is bigger than zone server count')

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
                STANDBY_MIN_MEMORY = 1073741824 * 2
                STANDBY_WARN_MEMORY = 1073741824 * 4
                STANDBY_MIN_LOG_DISK_SIZE = 1073741824 * 4

                if cpu_available < MIN_CPU:
                    return error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list, available=cpu_available, need=MIN_CPU))
                if mem_available < MIN_MEMORY:
                    return error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(mem_available), need=Capacity(MIN_MEMORY)))
                if log_disk_available < MIN_LOG_DISK_SIZE:
                    return error('{zone} not enough log_disk. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(log_disk_available), need=Capacity(MIN_LOG_DISK_SIZE)))

                recreate_cmd = ''
                check_available_param = {}
                check_available_param['max_cpu'] = [int(cpu_available), '']
                check_available_param['min_cpu'] = [int(cpu_available), '']
                check_available_param['memory_size'] = [mem_available, 'B']
                check_available_param['log_disk_size'] = [disk_available, 'B']
                for param, param_info in check_available_param.items():
                    if get_option(options, param, None) is None and param_info[0] < primary_tenant_info[param]:
                        recreate_cmd += ' --{}={}{} '.format(param, param_info[0], param_info[1])
                        stdio.warn("available {} is less then primary tenant's {} quota, primary tenant's {}{}, current available:{}{}".format(param, param, primary_tenant_info[param], param_info[1], param_info[0], param_info[1]))

                if recreate_cmd:
                    stdio.error("Resource confirmation: if you insist to take the risk, please recreate the tenant with '{}'".format(recreate_cmd))
                    return

                # cpu options
                max_cpu = get_option(options, 'max_cpu', cpu_available)
                min_cpu = get_option(options, 'min_cpu', max_cpu)
                if cpu_available < max_cpu:
                    return error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list, available=cpu_available, need=max_cpu))
                if max_cpu < min_cpu:
                    return error('min_cpu must less then max_cpu')
                if min_cpu < MIN_CPU:
                    return error('min_cpu must greater then %s' % MIN_CPU)

                # memory options
                memory_size = get_parsed_option('memory_size', None)
                log_disk_size = get_parsed_option('log_disk_size', None)

                if memory_size is None:
                    memory_size = mem_available
                if log_disk_size is None:
                    log_disk_size = log_disk_available

                if mem_available < memory_size:
                    return error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(mem_available), need=Capacity(memory_size)))
                if memory_size < MIN_MEMORY:
                    return error('memory must greater then %s' % Capacity(MIN_MEMORY))

                # log disk size options
                if log_disk_size is not None and log_disk_available < log_disk_size:
                    return error('{zone} not enough log_disk. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(log_disk_available), need=Capacity(log_disk_size)))

                if Capacity(primary_memory_size).bytes < STANDBY_MIN_MEMORY:
                    return error('Primary tenant memory_size:{}B is less than {}B, creating a standby tenant is not supported.'.format(primary_memory_size, STANDBY_MIN_MEMORY))
                if Capacity(primary_memory_size).bytes < STANDBY_WARN_MEMORY:
                    stdio.warn('Primary tenant memory_size: {}B , suggestion: {}B'.format(primary_memory_size, STANDBY_WARN_MEMORY))
                if Capacity(primary_log_disk_size).bytes < STANDBY_MIN_LOG_DISK_SIZE:
                    return error('Primary tenant log_disk_size:{}B is less than {}B, creating a standby tenant is not supported.'.format(primary_log_disk_size, STANDBY_MIN_LOG_DISK_SIZE))

                # iops options
                max_iops = get_option(options, 'max_iops', None)
                min_iops = get_option(options, 'min_iops', None)
                iops_weight = get_option(options, 'iops_weight', None)
                if max_iops is not None and max_iops < MIN_IOPS:
                    return error('max_iops must greater than %d' % MIN_IOPS)
                if max_iops is not None and min_iops is not None and max_iops < min_iops:
                    return error('min_iops must less then max_iops')

                zone_num = len(zones)
                replica_num = get_option(options, 'replica_num', zone_num)
                logonly_replica_num = get_option(options, 'logonly_replica_num', 0)
                primary_zone = get_option(options, 'primary_zone', 'RANDOM')

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

                res = cursor.execute(sql, stdio=stdio)
                if res is False:
                    error()
                    return

                # create resource pool
                sql = "create resource pool %s unit='%s', unit_num=%d, zone_list=%s" % (pool_name, unit_name, unit_num, zone_list)
                try:
                    cursor.execute(sql, raise_exception=True, stdio=stdio)
                except Exception as e:
                    stdio.exception('create resource pool failed, you can try again by using SQL "drop resource pool {}" to delete the resource pool, if you are certain that the resource pool is not being used. error info: {}'.format(pool_name, e))
                    stdio.stop_loading('failed')
                    return

                variables_dict[name] = {
                    'tenant_exists': tenant_exists,
                    'pool_name': pool_name,
                    'unit_name': unit_name,
                    'unit_num': unit_num
                }

                set_plugin_context_variables(plugin_context, variables_dict)

                stdio.stop_loading('succeed')

    return plugin_context.return_true()