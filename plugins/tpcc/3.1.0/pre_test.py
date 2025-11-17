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
import re

from ssh import LocalClient
from tool import DirectoryUtil

from ssh import LocalClient
from const import TOOL_TPCC, TOOL_TPCC_BENCHMARKSQL, COMP_OBCLIENT, COMP_JRE, COMP_OB_SEEKDB
from tool import get_option

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


def pre_test(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    repository = kwargs.get("repository")

    tmp_dir = os.path.abspath(get_option(options, 'tmp_dir', './tmp'))
    tenant_name = get_option(options, 'tenant', 'test') if repository.name != COMP_OB_SEEKDB else 'sys'

    sys_namespace = kwargs.get("sys_namespace")
    get_db_and_cursor = kwargs.get("get_db_and_cursor")
    db, cursor = get_db_and_cursor(sys_namespace)

    if tenant_name == 'sys' and repository.name != COMP_OB_SEEKDB:
        stdio.error('DO NOT use sys tenant for testing.')
        return

    bmsql_path = get_option(options, 'bmsql_dir')
    bmsql_jar = get_option(options, 'bmsql_jar', None)
    bmsql_libs = get_option(options, 'bmsql_libs', None)
    bmsql_sql_path = get_option(options, 'bmsql_sql_dir')
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

    obclient_bin = get_option(options, 'obclient_bin', 'obclient')
    cmd = '%s --help'
    path, result = file_path_check(obclient_bin, COMP_OBCLIENT, 'bin/obclient', cmd, stdio)
    if result is not None:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (
                result.stderr, obclient_bin))
        return
    obclient_bin = path
    setattr(options, 'obclient_bin', obclient_bin)

    java_bin = get_option(options, 'java_bin', 'java')
    cmd = '%s -version'
    path, result = file_path_check(java_bin, COMP_JRE, 'bin/java', cmd, stdio)
    if result is not None:
        path, result = file_path_check(java_bin, TOOL_TPCC, 'lib/bin/java', cmd, stdio)
        if result is not None:
            stdio.error(
                '%s\n%s is not an executable file. please use `--java-bin` to set.\nYou may not have java installed' % (
                    result.stderr, java_bin))
            return
    java_bin = path
    setattr(options, 'java_bin', java_bin)

    exec_classes = ['jTPCC', 'LoadData', 'ExecJDBC']
    passed = True
    for exec_class in exec_classes:
        ret = LocalClient.execute_command('%s -cp %s %s' % (java_bin, bmsql_classpath, exec_class), stdio=stdio)
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
        cpu_count_key = plugin_context.get_variable('cpu_count_key')
        cpu_count_value = plugin_context.get_variable('cpu_count_value', 0)
        query_sql = plugin_context.get_variable('active_sql')

        all_services = cursor.fetchall(query_sql)
        if not all_services:
            stdio.error('No active server available.')
            return
        for serv in all_services:
            cpu_count = int(serv.get(cpu_count_key, 0) + cpu_count_value)
            min_cpu = cpu_count if min_cpu is None else min(cpu_count, min_cpu)
            cpu_total += cpu_count
        server_num = len(all_services)
    except Exception as e:
        stdio.exception(e)
        stdio.error('Fail to get server status')
        return

    stdio.verbose('cpu total in all servers is %d' % cpu_total)
    if not bmsql_sql_path:
        sql_oceanbase_path = plugin_context.get_variable('sql_oceanbase_path')
        bmsql_sql_path = os.path.join(tmp_dir, 'sql.oceanbase')
        if not DirectoryUtil.copy(sql_oceanbase_path, bmsql_sql_path, stdio):
            return
        create_table_sql = os.path.join(bmsql_sql_path, 'tableCreates.sql')
        LocalClient.execute_command("sed -i 's/{{partition_num}}/%d/g' %s" % (cpu_total, create_table_sql), stdio=stdio)

    query_tenant_sql = plugin_context.get_variable('tenant_sql')
    tenant_meta = cursor.fetchone(query_tenant_sql, [tenant_name])
    if not tenant_meta:
        stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
        return

    query_resource_sql = plugin_context.get_variable('resource_sql')
    tenant_id = plugin_context.get_variable('tenant_id')

    sql = query_resource_sql % tenant_meta[tenant_id]
    pool = cursor.fetchone(sql)
    if pool is False:
        return

    query_unit_sql = plugin_context.get_variable('unit_sql')
    unit_config_id = plugin_context.get_variable('unit_config_id')

    sql = query_unit_sql % pool[unit_config_id]
    tenant_unit = cursor.fetchone(sql)
    if tenant_unit is False:
        return

    max_memory = tenant_unit[plugin_context.get_variable('max_memory')]
    max_cpu = int(tenant_unit[plugin_context.get_variable('max_cpu')])

    host = get_option(options, 'host', '127.0.0.1')
    port = db.port if db else 2881
    db_name = get_option(options, 'database', 'test')
    user = get_option(options, 'user', 'root')
    password = get_option(options, 'password', '')
    warehouses = get_option(options, 'warehouses', cpu_total * 20)
    load_workers = get_option(options, 'load_workers', int(max(min(min_cpu, (max_memory >> 30) / 2), 1)))
    terminals = get_option(options, 'terminals', min(cpu_total * 15, warehouses * 10))
    run_mins = get_option(options, 'run_mins', 10)
    test_only = get_option(options, 'test_only')

    stdio.verbose('Check connect ready')
    if not test_only:
        exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A -e" % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '')
        ret = LocalClient.execute_command('%s "%s" -E' % (exec_sql_cmd, 'create database if not exists %s' % db_name), stdio=stdio)
    else:
        exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A %s -e" % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', db_name)
        ret = LocalClient.execute_command('%s "%s" -E' % (exec_sql_cmd, 'select version();'), stdio=stdio)
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
        ret = LocalClient.execute_command('%s "%s" -E' % (exec_sql_cmd, 'select count(*) from bmsql_warehouse'), stdio=stdio)
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
        tenant_id=tenant_meta[tenant_id],
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
