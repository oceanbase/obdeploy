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
import re

from _errno import EC_OBSERVER_CAN_NOT_MIGRATE_IN
from _types import Capacity


def create_tenant(plugin_context, create_tenant_options=[], cursor=None, scale_out_component='',  *args, **kwargs):
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
        
    stdio = plugin_context.stdio
    multi_options = create_tenant_options if create_tenant_options else [plugin_context.options]
    if scale_out_component in ['ocp-server-ce', 'ocp-express']:
        multi_options = plugin_context.get_return('parameter_pre', spacename=scale_out_component).get_return('create_tenant_options')
    stdio.verbose('create_tenant options: %s' % multi_options)
    cursor = plugin_context.get_return('connect', spacename='oceanbase-ce').get_return('cursor') if not cursor else cursor
    for options in multi_options:
        create_if_not_exists = get_option('create_if_not_exists', False)
        tenant_exists = False
        plugin_context.set_variable('tenant_exists', tenant_exists)
        mode = get_option('mode', 'mysql').lower()
        if not mode in ['mysql', 'oracle']:
            error('No such tenant mode: %s.\n--mode must be `mysql` or `oracle`' % mode)
            return plugin_context.return_false()

        name = get_option('tenant_name', 'test')
        unit_name = '%s_unit' % name
        pool_name = '%s_pool' % name
        sql = "select tenant_name from oceanbase.gv$tenant where tenant_name = '%s'" % name
        res = cursor.fetchone(sql)
        if res:
            plugin_context.set_variable('tenant_exists', True)
            if create_if_not_exists:
                continue
            else:
                error('Tenant %s already exists' % name)
                return plugin_context.return_false()
        elif res is False:
            return plugin_context.return_false()
        if not tenant_exists:
            stdio.start_loading('Create tenant %s' % name)
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

            min_unit_num = min(zone_obs_num.items(), key=lambda x: x[1])[1]
            unit_num = get_option('unit_num', min_unit_num)
            if unit_num > min_unit_num:
                error('resource pool unit num is bigger than zone server count')
                return plugin_context.return_false()

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
                    return plugin_context.return_false()
            except:
                stdio.stop_loading('fail')
                return plugin_context.return_false()

            sql = "SELECT  min(cpu_total) cpu_total, min(mem_total) mem_total, min(disk_total) disk_total FROM oceanbase.__all_virtual_server_stat where zone in %s" % zone_list
            resource = cursor.fetchone(sql)
            if resource is False:
                stdio.stop_loading('fail')
                return plugin_context.return_false()
            cpu_total = resource['cpu_total']
            mem_total = resource['mem_total']
            disk_total = resource['disk_total']

            sql = 'select * from oceanbase.__all_resource_pool order by name'

            units_id = {}
            res = cursor.fetchall(sql)
            if res is False:
                stdio.stop_loading('fail')
                return plugin_context.return_false()
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
                return plugin_context.return_false()
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
                error('{zone} not enough cpu. (Available: {available}, Need: {need})'.format(zone=zone_list, available=cpu_total, need=MIN_CPU))
                return plugin_context.return_false()
            if mem_total < MIN_MEMORY:
                error('{zone} not enough memory. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(mem_total), need=Capacity(MIN_MEMORY)))
                return plugin_context.return_false()
            if disk_total < MIN_DISK_SIZE:
                error('{zone} not enough disk. (Available: {available}, Need: {need})'.format(zone=zone_list, available=Capacity(disk_total), need=Capacity(MIN_DISK_SIZE)))
                return plugin_context.return_false()

            try:
                max_memory = get_parsed_option('max_memory', mem_total)
                max_disk_size = get_parsed_option('max_disk_size', disk_total)
                min_memory = get_parsed_option('min_memory', max_memory)
            except Exception as e:
                error(e)
                return plugin_context.return_false()

            max_cpu = get_option('max_cpu', cpu_total)
            max_iops = get_option('max_iops', MIN_IOPS)
            max_session_num = get_option('max_session_num', MIN_SESSION_NUM)
            min_cpu = get_option('min_cpu', max_cpu)
            min_iops = get_option('min_iops', max_iops)

            if cpu_total < max_cpu:
                error('resource not enough: cpu (Avail: %s, Need: %s)' % (cpu_total, max_cpu))
                return plugin_context.return_false()
            if mem_total < max_memory:
                error('resource not enough: memory (Avail: %s, Need: %s)' % (Capacity(mem_total), Capacity(max_memory)))
                return plugin_context.return_false()
            if disk_total < max_disk_size:
                error('resource not enough: disk space (Avail: %s, Need: %s)' % (Capacity(disk_total), Capacity(max_disk_size)))
                return plugin_context.return_false()

            if max_iops < MIN_IOPS:
                error('max_iops must greater than %d' % MIN_IOPS)
                return plugin_context.return_false()
            if max_session_num < MIN_SESSION_NUM:
                error('max_session_num must greater than %d' % MIN_SESSION_NUM)
                return plugin_context.return_false()

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
                error('replica_num cannot be greater than zone num (%s)' % zone_num)
                return plugin_context.return_false()
            if not primary_zone:
                primary_zone = 'RANDOM'
            if logonly_replica_num > replica_num:
                error('logonly_replica_num cannot be greater than replica_num (%s)' % replica_num)
                return plugin_context.return_false()

            # create resource unit
            sql = 'create resource unit %s max_cpu %.1f, max_memory %d, max_iops %d, max_disk_size %d, max_session_num %d, min_cpu %.1f, min_memory %d, min_iops %d'
            sql = sql % (unit_name, max_cpu, max_memory, max_iops, max_disk_size, max_session_num, min_cpu, min_memory, min_iops)
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                stdio.stop_loading('fail')
                return plugin_context.return_false()

            # create resource pool
            sql = "create resource pool %s unit='%s', unit_num=%d, zone_list=%s" % (pool_name, unit_name, unit_num, zone_list)
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                stdio.stop_loading('fail')
                return plugin_context.return_false()

            # create tenant
            sql = "create tenant %s replica_num=%d,zone_list=%s,primary_zone='%s',resource_pool_list=('%s')"
            sql = sql % (name, replica_num, zone_list, primary_zone, pool_name)
            if charset:
                sql += ", charset = '%s'" % charset
            if collate and mode == "mysql":
                sql += ", collate = '%s'" % collate
            if logonly_replica_num:
                sql += ", logonly_replica_num = %d" % logonly_replica_num
            if tablegroup:
                sql += ", default tablegroup ='%s'" % tablegroup
            if locality:
                sql += ", locality = '%s'" % locality

            set_mode = "ob_compatibility_mode = '%s'" % mode

            variables_map = {}
            ob_tcp_invited_nodes_value = None
            if variables:
                pattern = r"(\w+)\s*=\s*((?:'[^']*'|\"[^\"]*\"|[^,]+))"
                matches = re.findall(pattern, variables)
                for key, value in matches:
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                        value = value[1:-1]
                    if key == 'ob_tcp_invited_nodes':
                        ob_tcp_invited_nodes_value = value
                        value = "'%'"

                    variables_map[key] = value

            variables_str = ','.join(['{}={}'.format(k, v) for k, v in variables_map.items()])

            if ob_tcp_invited_nodes_value:
                tenant_whitelist = {}
                tenant_whitelist[name] = ob_tcp_invited_nodes_value
                plugin_context.set_variable('tenant_whitelist', tenant_whitelist)

            if variables_str:
                sql += "set %s, %s" % (variables_str, set_mode)
            else:
                sql += "set %s" % set_mode
            res = cursor.execute(sql, stdio=stdio)
            if res is False:
                stdio.stop_loading('fail')
                return plugin_context.return_false()

        stdio.stop_loading('succeed')
    plugin_context.set_variable('error', error)
    return plugin_context.return_true()
