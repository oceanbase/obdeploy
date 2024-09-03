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

import os
import time

import const
from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN
from _types import Capacity
from tool import Exector

tenant_cursor = None


def exec_sql_in_tenant(sql, cursor, tenant, mode, retries=10, args=[], stdio=None):
    global tenant_cursor
    if not tenant_cursor:
        user = 'SYS' if mode == 'oracle' else 'root'
        tenant_cursor = cursor.new_cursor(tenant=tenant, user=user)
        if not tenant_cursor and retries:
            retries -= 1
            time.sleep(2)
            return exec_sql_in_tenant(sql, cursor, tenant, mode, retries=retries, args=args, stdio=stdio)
    return tenant_cursor.execute(sql, args=args, stdio=stdio)


def create_tenant(plugin_context, create_tenant_options=[], cursor=None,  *args, **kwargs):
    def get_option(key, default=''):
        if key in kwargs:
            return kwargs[key]
        value = getattr(options, key, default)
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
        
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    for options in multi_options:
        cursor = plugin_context.get_return('connect').get_return('cursor') if not cursor else cursor
        create_if_not_exists = get_option('create_if_not_exists', False)
        tenant_exists = False
        global tenant_cursor
        tenant_cursor = None

        mode = get_option('mode', 'mysql').lower()
        if not mode in ['mysql', 'oracle']:
            error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
            return 

        name = get_option('tenant_name', 'test')
        unit_name = '%s_unit' % name
        pool_name = '%s_pool' % name
        sql = "select tenant_name from oceanbase.gv$tenant where tenant_name = '%s'" % name
        res = cursor.fetchone(sql)
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
                stdio.stop_loading('fail')
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
            try:
                while count:
                    num = cursor.fetchone(sql, raise_exception=True)['num']
                    if num >= unit_num:
                        break
                    count -= 1
                    time.sleep(1)
                if count == 0:
                    stdio.error(EC_OBSERVER_CAN_NOT_MIGRATE_IN)
                    return
            except:
                stdio.stop_loading('fail')
                return

            cpu_total = 0
            mem_total = 0
            disk_total = 0
            sql = "SELECT  min(cpu_total) cpu_total, min(mem_total) mem_total, min(disk_total) disk_total FROM oceanbase.__all_virtual_server_stat where zone in %s" % zone_list
            resource = cursor.fetchone(sql)
            if resource is False:
                stdio.stop_loading('fail')
                return
            cpu_total = resource['cpu_total']
            mem_total = resource['mem_total']
            disk_total = resource['disk_total']

            sql = 'select * from oceanbase.__all_resource_pool order by name'

            units_id = {}
            res = cursor.fetchall(sql)
            if res is False:
                stdio.stop_loading('fail')
                return
            for row in res:
                if str(row['name']) == unit_name:
                    unit_name += '1'
                if row['tenant_id'] < 1:
                    continue
                for zone in str(row['zone_list']).replace(';', ',').split(','):
                    if zone in zones:
                        unit_config_id = row['unit_config_id']
                        units_id[unit_config_id] = units_id.get(unit_config_id, 0) + 1
                        break

            sql = 'select * from oceanbase.__all_unit_config order by name'
            res = cursor.fetchall(sql)
            if res is False:
                stdio.stop_loading('fail')
                return
            for row in res:
                if str(row['name']) == unit_name:
                    unit_name += '1'
                if row['unit_config_id'] in units_id:
                    cpu_total -= row['max_cpu'] * units_id[row['unit_config_id']]
                    mem_total -= row['max_memory'] * units_id[row['unit_config_id']]
                    # disk_total -= row['max_disk_size']

            MIN_CPU = 2
            MIN_MEMORY = 1073741824
            MIN_DISK_SIZE = 536870912
            MIN_IOPS = 128
            MIN_SESSION_NUM = 64
            if cpu_total < MIN_CPU:
                return error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list, available=cpu_total, need=MIN_CPU))
            if mem_total < MIN_MEMORY:
                return error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(mem_total), need=Capacity(MIN_MEMORY)))
            if disk_total < MIN_DISK_SIZE:
                return error('{zone} not enough disk. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(disk_total), need=Capacity(MIN_DISK_SIZE)))

            try:
                max_memory = get_parsed_option('max_memory', mem_total)
                max_disk_size = get_parsed_option('max_disk_size', disk_total)
                min_memory = get_parsed_option('min_memory', max_memory)
            except Exception as e:
                error(e)
                return

            max_cpu = get_option('max_cpu', cpu_total)
            max_iops = get_option('max_iops', MIN_IOPS)
            max_session_num = get_option('max_session_num', MIN_SESSION_NUM)
            min_cpu = get_option('min_cpu', max_cpu)
            min_iops = get_option('min_iops', max_iops)

            if cpu_total < max_cpu:
                return error('resource not enough: cpu (Avail: %s, Need: %s)' % (cpu_total, max_cpu))
            if mem_total < max_memory:
                return error('resource not enough: memory (Avail: %s, Need: %s)' % (Capacity(mem_total), Capacity(max_memory)))
            if disk_total < max_disk_size:
                return error('resource not enough: disk space (Avail: %s, Need: %s)' % (Capacity(disk_total), Capacity(max_disk_size)))

            if max_iops < MIN_IOPS:
                return error('max_iops must greater than %d' % MIN_IOPS)
            if max_session_num < MIN_SESSION_NUM:
                return error('max_session_num must greater than %d' % MIN_SESSION_NUM)

            if max_cpu < min_cpu:
                return error('min_cpu must less then max_cpu')
            if max_memory < min_memory:
                return error('min_memory must less then max_memory')
            if max_iops < min_iops:
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
            sql = 'create resource unit %s max_cpu %.1f, max_memory %d, max_iops %d, max_disk_size %d, max_session_num %d, min_cpu %.1f, min_memory %d, min_iops %d'
            sql = sql % (unit_name, max_cpu, max_memory, max_iops, max_disk_size, max_session_num, min_cpu, min_memory, min_iops)
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                stdio.stop_loading('fail')
                return

            # create resource pool
            sql = "create resource pool %s unit='%s', unit_num=%d, zone_list=%s" % (pool_name, unit_name, unit_num, zone_list)
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                stdio.stop_loading('fail')
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
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                stdio.stop_loading('fail')
                return

        stdio.stop_loading('succeed')

        database = get_option('database')
        if database:
            sql = 'create database {}'.format(database)
            if not exec_sql_in_tenant(sql=sql, cursor=cursor, tenant=name, mode=mode, stdio=stdio) and not create_if_not_exists:
                stdio.error('failed to create database {}'.format(database))
                return

        db_username = get_option('db_username')
        db_password = get_option('db_password', '')
        if db_username:
            create_sql, grant_sql = "", ""
            if mode == "mysql":
                create_sql = "create user if not exists '{username}' IDENTIFIED BY %s;".format(username=db_username)
                grant_sql = "grant all on *.* to '{username}' WITH GRANT OPTION;".format(username=db_username)
            else:
                error("Create user in oracle tenant is not supported")
            if not exec_sql_in_tenant(sql=create_sql, cursor=cursor, tenant=name, mode=mode, args=[db_password], stdio=stdio):
                stdio.error('failed to create user {}'.format(db_username))
                return
            if not exec_sql_in_tenant(sql=grant_sql, cursor=cursor, tenant=name, mode=mode, stdio=stdio):
                stdio.error('Failed to grant privileges to user {}'.format(db_username))
                return

        clients = plugin_context.clients
        repositories = plugin_context.repositories
        client = clients[plugin_context.cluster_config.servers[0]]
        cluster_config = plugin_context.cluster_config
        global_config = cluster_config.get_global_conf()

        time_zone = get_option('time_zone', client.execute_command('date +%:z').stdout.strip())
        exec_sql_in_tenant(sql="SET GLOBAL time_zone='%s';" % time_zone, cursor=cursor, tenant=name, mode=mode, args=[db_password], stdio=stdio)

        exector_path = get_option('exector_path', '/usr/obd/lib/executer')
        exector = Exector(tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user, tenant_cursor.password, exector_path, stdio)
        for repository in repositories:
            if repository.name in const.COMPS_OB:
                time_zone_info_param = os.path.join(repository.repository_dir, 'etc', 'timezone_V1.log')
                if not exector.exec_script('import_time_zone_info.py', repository, param="-h {} -P {} -t {} -p '{}' -f {}".format(tenant_cursor.ip, tenant_cursor.port, name, global_config.get("root_password", ''), time_zone_info_param)):
                    stdio.warn('execute import_time_zone_info.py failed')
                break
        cmd = 'obclient -h%s -P%s -u%s -Doceanbase -A\n' % (tenant_cursor.ip, tenant_cursor.port, tenant_cursor.user)
        stdio.print(cmd)
    return plugin_context.return_true()
