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

import os
import time
from collections import defaultdict
from copy import deepcopy

import const
from _stdio import IO
from tool import Exector
from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN
from _types import Capacity


def dump_standby_relation(relation_tenants, cluster_configs, dump_relation_tenants, stdio):
    # find all relation tenant
    deploy_name_tenants = deepcopy(relation_tenants)
    deploy_name_tenants.extend(dump_relation_tenants)
    for deploy_name_tenant_tup in deploy_name_tenants:
        relation_deploy_name = deploy_name_tenant_tup[0]
        relation_tenant_name = deploy_name_tenant_tup[1]
        for deploy_name_tenant_inner in deploy_name_tenants:
            if (relation_deploy_name, relation_tenant_name) != tuple(deploy_name_tenant_inner):
                _dump_standby_relation(relation_deploy_name, relation_tenant_name, deploy_name_tenant_inner, cluster_configs.get(relation_deploy_name), stdio)
    for cluster_config in cluster_configs.values():
        cluster_config.update_component_attr('standby_relation', cluster_config.get_component_attr('standby_relation'), save=True)
    return True


def _dump_standby_relation(deploy_name, tenant_name, dump_relation_tenant, cluster_config, stdio):
    stdio.verbose('dump standby relation, deploy_name:{}, tenant_name:{},dump_relation_tenant:{}'.format(deploy_name, tenant_name, dump_relation_tenant))
    if not cluster_config:
        stdio.verbose('dump_standby_relation: No such deploy: %s.' % deploy_name)
        return False
    relation_dict = cluster_config.get_component_attr('standby_relation')
    if relation_dict:
        relation_tenants = relation_dict.get(tenant_name, [])
        if not relation_tenants:
            relation_dict[tenant_name] = [dump_relation_tenant]
        elif tuple(dump_relation_tenant) not in [tuple(t) for t in relation_tenants]:
            relation_tenants.append(dump_relation_tenant)
    else:
        relation_dict = {tenant_name: [dump_relation_tenant]}
    cluster_config.update_component_attr('standby_relation', relation_dict, save=False)
    return True


def dump_standbyro_password(deploy_name, tenant_name, standbyro_password, cluster_config, stdio):
    if not cluster_config:
        stdio.error('No such deploy: %s.' % deploy_name)
        return False
    standbyro_password_dict = cluster_config.get_component_attr('standbyro_password')
    if standbyro_password_dict:
        standbyro_password_dict[tenant_name] = standbyro_password
    else:
        standbyro_password_dict = {tenant_name: standbyro_password}
    cluster_config.update_component_attr('standbyro_password', standbyro_password_dict, save=True)
    return True


def create_standby_tenant(plugin_context, config_encrypted, cursor=None, create_tenant_options=[], relation_tenants={}, cluster_configs={}, primary_tenant_info={}, standbyro_password='', *args, **kwargs):
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
    for options in multi_options:
        create_if_not_exists = get_option('create_if_not_exists', False)
        standby_deploy_name = plugin_context.cluster_config.deploy_name
        cursor = plugin_context.get_return('connect').get_return('cursor') if not cursor else cursor
        cursor = cursor if cursor else plugin_context.get_variable('cursors').get(standby_deploy_name)
        global tenant_cursor
        tenant_cursor = None
        zone_list = get_option('zone_list', set())
        locality = get_option('locality', '')
        primary_zone = get_option('primary_zone', 'RANDOM')

        if primary_tenant_info:
            primary_deploy_name = primary_tenant_info.get('primary_deploy_name')
            primary_tenant = primary_tenant_info.get('primary_tenant')
            primary_cursor = plugin_context.get_variable('cursors').get(primary_deploy_name)
            primary_memory_size = primary_tenant_info['memory_size']
            primary_log_disk_size = primary_tenant_info['log_disk_size']
            primary_params = ['max_cpu', 'min_cpu', 'unit_num', 'memory_size', 'log_disk_size', 'max_iops', 'min_iops', 'iops_weight']
            for param in primary_params:
                if get_option(param, None) is None and param in primary_tenant_info:
                    setattr(options, param, primary_tenant_info[param])

            mode = get_option('mode', 'mysql').lower()
            if not mode in ['mysql', 'oracle']:
                error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
                return

            # options not support
            deserted_options = ('max_session_num', 'max_memory', 'min_memory', 'max_disk_size')
            for opt in deserted_options:
                if get_option(opt, None) is not None:
                    stdio.warn("option {} is no longer supported".format(opt))

            name = get_option('tenant_name', primary_tenant)
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
                    if get_option(param, None) is None and param_info[0] < primary_tenant_info[param]:
                        recreate_cmd += ' --{}={}{} '.format(param, param_info[0], param_info[1])
                        stdio.warn("available {} is less then primary tenant's {} quota, primary tenant's {}{}, current available:{}{}".format(param, param, primary_tenant_info[param], param_info[1], param_info[0], param_info[1]))

                if recreate_cmd:
                    stdio.error("Resource confirmation: if you insist to take the risk, please recreate the tenant with '{}'".format(recreate_cmd))
                    return

                # cpu options
                max_cpu = get_option('max_cpu', cpu_available)
                min_cpu = get_option('min_cpu', max_cpu)
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
                variables = get_option('variables', "ob_tcp_invited_nodes='%'")

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
                    return

                # create standby tenant
                # query ip_list
                sql = '''select group_concat(host separator ";") as ip_list from (select concat(svr_ip,":",SQL_PORT) as host  from oceanbase.cdb_ob_access_point where tenant_name=%s)'''
                res = primary_cursor.fetchone(sql, (primary_tenant, ))
                if not res:
                    stdio.error('ip_list query error.')
                    return

                sql = '''CREATE STANDBY TENANT {} LOG_RESTORE_SOURCE = 'SERVICE={} USER=standbyro@{} PASSWORD={}' RESOURCE_POOL_LIST=('{}') , primary_zone='{}' '''.format(name, res['ip_list'], primary_tenant, standbyro_password, pool_name, primary_zone)
                if locality:
                    sql += ", locality = '%s'" % locality

                try:
                    cursor.execute(sql, raise_exception=True, exc_level='verbose', stdio=stdio)
                except Exception as e:
                    stdio.verbose('create standby tenant fail, clean and retry.  fail message:{}'.format(e))
                    # clean and retry create standby tenant
                    res = cursor.fetchone("select TENANT_ID from oceanbase.DBA_OB_TENANTS where tenant_name = %s", (name, ), raise_exception=False)
                    if res is False:
                        error('Create standby tenant fail. message:{}'.format(e))
                        return
                    if res:
                        # drop tenant
                        tenant_id = res['TENANT_ID']
                        res = cursor.execute("drop tenant %s FORCE" % name, raise_exception=False, stdio=stdio)
                        if res is False:
                            error('Create standby tenant fail. message:{}'.format(e))
                            return

                        # wait drop tenant
                        count = 600
                        while count > 0:
                            res = cursor.fetchone('select count(1) as count from oceanbase.GV$OB_UNITS where TENANT_ID=%s or TENANT_ID=%s', (tenant_id, int(tenant_id)-1), raise_exception=False)
                            if res is False:
                                error('query unit info failed')
                                return
                            if res['count'] == 0:
                                break
                            count -= 1
                            time.sleep(1)

                        if count == 0:
                            error('Retry create standby tenant failed: drop tenant timeout')
                            return

                    # create again
                    try:
                        cursor.execute(sql, raise_exception=True, stdio=stdio)
                    except Exception as e:
                        retry_message = 'After resolving this issue, you can clean up the environment by manually executing "obd cluster tenant drop {} -t {}", and then wait for a while before re-creating the standby tenant.'.format(standby_deploy_name, name)
                        error("create standby tenant failed, error: {}".format(IO.log_masking_static(e.__str__()) if config_encrypted else e))
                        stdio.print(retry_message)
                        return
                stdio.stop_loading('succeed')

                # check standby sync status
                stdio.start_loading('Check standby sync status')
                sql = "SELECT tenant_id, tenant_name, tenant_type, primary_zone, locality, compatibility_mode, status, in_recyclebin, (CASE WHEN LOCKED = 'YES' THEN 1 ELSE 0 END) AS locked, TIMESTAMPDIFF(SECOND, CREATE_TIME, now()) AS exist_seconds, arbitration_service_status, switchover_status, log_mode, sync_scn, recovery_until_scn, tenant_role FROM oceanbase.DBA_OB_TENANTS WHERE TENANT_TYPE IN ('SYS', 'USER') and tenant_name = %s"
                res = cursor.fetchone(sql, (name, ))
                if not res:
                    error('check standby sync status failed')
                    return

                stdio.print_list([res], ['tenant_name', 'log_mode', 'locality', 'tenant_role', 'create_status'],
                    lambda x: [x['tenant_name'], x['log_mode'], x['locality'], x['tenant_role'], x['status']], title='standby tenant info')

                if res['status'] != 'NORMAL':
                    error('standby tenant status is not normal')
                    return
                stdio.stop_loading('succeed')

                stdio.start_loading('Dump standby relation')
                if not dump_standbyro_password(standby_deploy_name, name, standbyro_password, cluster_configs.get(standby_deploy_name), stdio):
                    return
                if not dump_standby_relation(relation_tenants, cluster_configs, [[standby_deploy_name, name], [primary_deploy_name, primary_tenant]], stdio):
                    return
                stdio.stop_loading('succeed')

                # check log sync task create
                stdio.start_loading('Creating log sync task')
                sql = "SELECT tenant_id, REPLACE(`sync_status`, ' ', '_') as sync_status, err_code, comment FROM oceanbase.V$OB_LS_LOG_RESTORE_STATUS  WHERE tenant_id = %s group by sync_status "
                count = 600
                while count > 0:
                    sync_status_res = cursor.fetchall(sql, (res['tenant_id'], ))
                    if sync_status_res and sync_status_res[0].get('sync_status') != 'WAITING_LS_CREATED':
                        break
                    count -= 1
                    time.sleep(1)
                stdio.verbose('Wait log sync create: retry {}'.format(200 - count))
                if count == 0:
                    stdio.warn('wait log sync create timeout')

                flag = False
                for item in sync_status_res:
                    if item.get('sync_status') != 'NORMAL':
                        flag = True
                        stdio.error('standby tenant log sync error, tenant_id:{}, sync_status:{}, err_code:{},comment:{}'.format(item['tenant_id'], item['sync_status'], item['err_code'], item['comment']))

                if flag:
                    stdio.stop_loading('failed')
                stdio.stop_loading('succeed')

                stdio.print('You can use the command "obd cluster tenant show {} -g" to view the relationship between the primary and standby tenants.'.format(standby_deploy_name))

    return plugin_context.return_true()
