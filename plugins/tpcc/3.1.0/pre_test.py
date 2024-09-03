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
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import os
import re

from ssh import LocalClient
from tool import DirectoryUtil
from const import TOOL_TPCC, TOOL_TPCC_BENCHMARKSQL, COMP_OBCLIENT

PROPS4OB_TEMPLATE = """
db=oceanbase
driver=com.mysql.jdbc.Driver
conn=jdbc:mysql://{host_ip}:{port}/{db_name}?rewriteBatchedStatements=true&allowMultiQueries=true&useLocalSessionState=true&useUnicode=true&characterEncoding=utf-8&socketTimeout=30000000&useSSL=false
user={user}
password={password}
warehouses={warehouses}
loadWorkers={load_workers}
terminals={terminals}
database={db_name}
runTxnsPerTerminal=0
runMins={run_mins}
limitTxnsPerMin=0
terminalWarehouseFixed=true
newOrderWeight=45
paymentWeight=43
orderStatusWeight=4
deliveryWeight=4
stockLevelWeight=4
resultDirectory=my_result_%tY-%tm-%td_%tH%tM%tS
osCollectorScript=./misc/os_collector_linux.py
osCollectorInterval=1
"""

def file_path_check(bin_path, tool_name, tool_path, cmd, stdio):
    result = None
    tool_path = os.path.join(os.getenv('HOME'), tool_name, tool_path)
    for path in [bin_path, tool_path]:
        result = LocalClient.execute_command(cmd % path, stdio=stdio)
        if not result:
            continue
        break
    else:
        return None, result
    return path, None

def pre_test(plugin_context, cursor, odp_cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        stdio.verbose('get option: {} value {}'.format(key, value))
        return value

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    stdio = plugin_context.stdio
    options = plugin_context.options

    tmp_dir = os.path.abspath(get_option('tmp_dir', './tmp'))
    tenant_name = get_option('tenant', 'test')

    if tenant_name == 'sys':
        stdio.error('DO NOT use sys tenant for testing.')
        return

    bmsql_path = get_option('bmsql_dir')
    bmsql_jar = get_option('bmsql_jar', None)
    bmsql_libs = get_option('bmsql_libs', None)
    bmsql_sql_path = get_option('bmsql_sql_dir')
    if bmsql_path:
        if bmsql_jar is None:
            bmsql_jar = os.path.join(bmsql_path, 'dist') if bmsql_path else '/usr/ob-benchmarksql/OB-BenchmarkSQL-5.0.jar'
        if bmsql_libs is None:
            bmsql_libs = '%s,%s' % (os.path.join(bmsql_path, 'lib'), os.path.join(bmsql_path, 'lib/oceanbase'))
    else:
        if bmsql_jar is None:
            bmsql_jar = '/usr/ob-benchmarksql/OB-BenchmarkSQL-5.0.jar'

    if not os.path.exists(tmp_dir) and not DirectoryUtil.mkdir(tmp_dir):
        stdio.error('Create tmp dir failed')
        return

    bmsql_jar_paths = [bmsql_jar, os.path.join(os.getenv('HOME'), TOOL_TPCC, "tpcc/%s" % TOOL_TPCC_BENCHMARKSQL)]
    for jar_path in bmsql_jar_paths:
        if os.path.exists(jar_path):
            bmsql_jar = jar_path
            setattr(options, 'bmsql_dir', bmsql_jar)
            break
    else:
        stdio.error('BenchmarkSQL jar file not found at %s. Please use `--bmsql-jar` to set BenchmarkSQL jar file' % bmsql_jar)
        return

    if not os.path.exists(bmsql_jar):
        stdio.error(
            'BenchmarkSQL jar file not found at %s. Please use `--bmsql-jar` to set BenchmarkSQL jar file' % bmsql_jar)
        return

    jars = [os.path.join(bmsql_jar, '*') if os.path.isdir(bmsql_jar) else bmsql_jar]
    if bmsql_libs:
        for lib in bmsql_libs.split(','):
            if lib:
                if os.path.isdir(lib):
                    jars.append(os.path.join(lib, '*'))
                else:
                    jars.append(lib)
    bmsql_classpath = ':'.join(jars)

    obclient_bin = get_option('obclient_bin', 'obclient')
    cmd = '%s --help'
    path, result = file_path_check(obclient_bin, COMP_OBCLIENT, 'bin/obclient', cmd, stdio)
    if result:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (
                result.stderr, obclient_bin))
        return
    obclient_bin = path
    setattr(options, 'obclient_bin', obclient_bin)

    java_bin = get_option('java_bin', 'java')
    cmd = '%s -version'
    path, result = file_path_check(java_bin, TOOL_TPCC, 'lib/bin/java', cmd, stdio)
    if result:
        stdio.error(
            '%s\n%s is not an executable file. please use `--java-bin` to set.\nYou may not have java installed' % (
                result.stderr, java_bin))
        return
    java_bin = path
    setattr(options, 'java_bin', java_bin)

    exec_classes = ['jTPCC', 'LoadData', 'ExecJDBC']
    passed = True
    for exec_class in exec_classes:
        ret = local_execute_command('%s -cp %s %s' % (java_bin, bmsql_classpath, exec_class))
        if 'Could not find or load main class %s' % exec_class in ret.stderr:
            stdio.error('Main class %s not found.' % exec_class)
            passed = False
    if not passed:
        stdio.error('Please use `--bmsql-libs` to infer all the depends')
        return

    local_dir = os.path.dirname(os.path.abspath(__file__))
    run_path = os.path.join(tmp_dir, 'run')
    if not DirectoryUtil.copy(os.path.join(local_dir, 'run'), run_path, stdio):
        return

    stdio.verbose('Start to get bmsql sqls...')
    if bmsql_sql_path:
        miss_sql = []
        for sql_file in ['buildFinish.sql', 'indexCreates.sql', 'indexDrops.sql', 'tableCreates.sql', 'tableDrops.sql']:
            if not os.path.exists(os.path.join(bmsql_sql_path, sql_file)):
                miss_sql.append(sql_file)
        if miss_sql:
            stdio.error('Cannot find %s in scripts path %s.' % (','.join(miss_sql), bmsql_sql_path))
            stdio.stop_loading('fail')
            return

    cpu_total = 0
    min_cpu = None
    try:
        sql = "select a.id , b.cpu_total from oceanbase.__all_server a " \
              "join oceanbase.__all_virtual_server_stat b on a.id=b.id " \
              "where a.status = 'active' and a.stop_time = 0 and a.start_service_time > 0;"
        all_services = cursor.fetchall(sql)
        if not all_services:
            stdio.error('No active server available.')
            return
        for serv in all_services:
            cpu_count = int(serv.get('cpu_total', 0) + 2)
            min_cpu = cpu_count if min_cpu is None else min(cpu_count, min_cpu)
            cpu_total += cpu_count
        server_num = len(all_services)
    except Exception as e:
        stdio.exception(e)
        stdio.error('Fail to get server status')
        return

    stdio.verbose('cpu total in all servers is %d' % cpu_total)
    if not bmsql_sql_path:
        bmsql_sql_path = os.path.join(tmp_dir, 'sql.oceanbase')
        if not DirectoryUtil.copy(os.path.join(local_dir, 'sql.oceanbase'), bmsql_sql_path, stdio):
            return
        create_table_sql = os.path.join(bmsql_sql_path, 'tableCreates.sql')
        local_execute_command("sed -i 's/{{partition_num}}/%d/g' %s" % (cpu_total, create_table_sql))

    sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
    tenant_meta = cursor.fetchone(sql, [tenant_name])
    if not tenant_meta:
        stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
        return
    sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d" % tenant_meta['tenant_id']
    pool = cursor.fetchone(sql)
    if pool is False:
        return
    sql = "select * from oceanbase.__all_unit_config where unit_config_id = %d" % pool['unit_config_id']
    tenant_unit = cursor.fetchone(sql)
    if tenant_unit is False:
        return
    max_memory = tenant_unit['max_memory']
    max_cpu = int(tenant_unit['max_cpu'])

    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    db_name = get_option('database', 'test')
    user = get_option('user', 'root')
    password = get_option('password', '')
    warehouses = get_option('warehouses', cpu_total * 20)
    load_workers = get_option('load_workers', int(max(min(min_cpu, (max_memory >> 30) / 2), 1)))
    terminals = get_option('terminals', min(cpu_total * 15, warehouses * 10))
    run_mins = get_option('run_mins', 10)
    test_only = get_option('test_only')

    stdio.verbose('Check connect ready')
    if not test_only:
        exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A -e" % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '')
        ret = local_execute_command('%s "%s" -E' % (exec_sql_cmd, 'create database if not exists %s' % db_name))
    else:
        exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A %s -e" % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', db_name)
        ret = local_execute_command('%s "%s" -E' % (exec_sql_cmd, 'select version();'))
    if not ret:
        stdio.error('Connect to tenant %s failed' % tenant_name)
        return

    if warehouses <= 0:
        stdio.error('warehouses should more than 0')
        return
    if terminals <= 0 or terminals > 10 * warehouses:
        stdio.error('terminals should more than 0 and less than 10 * warehouses')
        return
    if run_mins <= 0:
        stdio.error('run-mins should more than 0')
        return
    if test_only:
        exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A %s -e" % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', db_name)
        table_rows = 0
        ret = local_execute_command('%s "%s" -E' % (exec_sql_cmd, 'select count(*) from bmsql_warehouse'))
        matched = re.match(r'.*count\(\*\):\s?(\d+)', ret.stdout, re.S)
        if matched:
            table_rows = int(matched.group(1))
        if table_rows <= 0:
            stdio.error('No warehouse found. Please load data first.')
            return
        elif table_rows != warehouses:
            stdio.error('Warehouse num do not match. Expect: {} ,actual: {}'.format(warehouses, table_rows))
            return
    try:
        bmsql_prop_path = os.path.join(tmp_dir, 'props.oceanbase')
        stdio.verbose('set bmsql_prop_path: {}'.format(bmsql_prop_path))
        with open(bmsql_prop_path, 'w') as f:
            f.write(PROPS4OB_TEMPLATE.format(
                host_ip=host,
                port=port,
                db_name=db_name,
                user=user + '@' + tenant_name,
                password=password,
                warehouses=warehouses,
                load_workers=load_workers,
                terminals=terminals,
                run_mins=run_mins
                ))
    except Exception as e:
        stdio.exception(e)
        stdio.error('Failed to generate config file props.oceanbase.')
        stdio.stop_loading('fail')
        return

    stdio.stop_loading('succeed')
    return plugin_context.return_true(
        bmsql_prop_path=bmsql_prop_path,
        bmsql_classpath=bmsql_classpath,
        run_path=run_path,
        bmsql_sql_path=bmsql_sql_path,
        warehouses=warehouses,
        cpu_total=cpu_total,
        max_memory=max_memory,
        max_cpu=max_cpu,
        tenant_id=tenant_meta['tenant_id'],
        tenant=tenant_name,
        tmp_dir=tmp_dir,
        server_num=server_num,
        obclient_bin=obclient_bin,
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name
    )
