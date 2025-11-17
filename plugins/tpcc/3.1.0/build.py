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

try:
    import subprocess32 as subprocess
except:
    import subprocess
import os
import time
import re

from ssh import LocalClient
from const import COMP_OB_SEEKDB
from tool import get_option


def build(plugin_context, *args, **kwargs):
    def run_sql(sql_file, force=False):
        sql_cmd = "{obclient} -h{host} -P{port} -u{user}@{tenant} {password_arg} -A {db} {force_flag} < {sql_file}".format(
            obclient=obclient_bin, host=host, port=port, user=user, tenant=tenant_name,
            password_arg=("-p'%s'" % password) if password else '',
            db=db_name,
            force_flag='-f' if force else '',
            sql_file=sql_file)
        return LocalClient.execute_command(sql_cmd, stdio=stdio)

    def get_table_rows(table_name):
        table_rows = 0
        ret = LocalClient.execute_command('%s "%s" -E' % (exec_sql_cmd, 'select count(*) from %s' % table_name), stdio=stdio)
        matched = re.match(r'.*count\(\*\):\s?(\d+)', ret.stdout, re.S)
        if matched:
            table_rows = int(matched.group(1))
        return table_rows

    stdio = plugin_context.stdio
    options = plugin_context.options
    pre_test_ret = plugin_context.get_return("pre_test")
    repository = kwargs.get("repository")

    server_state = plugin_context.get_variable('server_state')
    merge = plugin_context.get_variable('merge')

    bmsql_jar = get_option(options, 'bmsql_jar')
    bmsql_libs = get_option(options, 'bmsql_libs')

    host = get_option(options, 'host', '127.0.0.1')
    db_name = get_option(options, 'database', 'test')
    user = get_option(options, 'user', 'root')
    password = get_option(options, 'password', '')
    tenant_name = get_option(options, 'tenant', 'test') if repository.name != COMP_OB_SEEKDB else 'sys'
    obclient_bin = get_option(options, 'obclient_bin', 'obclient')
    java_bin = get_option(options, 'java_bin', 'java')

    sys_namespace = kwargs.get("sys_namespace")
    proxysys_namespace = kwargs.get("proxysys_namespace")
    get_db_and_cursor = kwargs.get("get_db_and_cursor")
    db, cursor = get_db_and_cursor(sys_namespace)
    odp_db, odp_cursor = get_db_and_cursor(proxysys_namespace)
    port = db.port if db else 2881

    bmsql_classpath = pre_test_ret.get_return("bmsql_classpath")
    if not bmsql_classpath:
        jars = [bmsql_jar]
        jars.extend(bmsql_libs.split(','))
        bmsql_classpath = '.:' + ':'.join(jars)
    bmsql_prop_path = pre_test_ret.get_return("bmsql_prop_path")
    stdio.verbose('get bmsql_prop_path: {}'.format(bmsql_prop_path))
    warehouses = pre_test_ret.get_return("warehouses", 0)

    stdio.verbose('Check connect ready')
    exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A %s -e" % (
        obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', db_name)
    stdio.start_loading('Connect to tenant %s' % tenant_name)
    try:
        while True:
            ret = LocalClient.execute_command('%s "%s" -E' % (exec_sql_cmd, 'select version();'), stdio=stdio)
            if ret:
                break
            time.sleep(10)
        stdio.stop_loading('succeed')
    except:
        stdio.stop_loading('fail')
        stdio.exception('')
        return
    stdio.start_loading('Server check')
    # check for observer
    while True:
        query_sql = plugin_context.get_variable('server_status_sql')
        ret = cursor.fetchone(query_sql)
        if ret is False:
            stdio.stop_loading('fail')
            return
        if ret is None:
            break
        time.sleep(3)
    # check for obproxy
    if odp_cursor:
        while True:
            sql = "show proxycongestion all"
            proxy_congestions = odp_cursor.fetchall(sql)
            if proxy_congestions is False:
                stdio.stop_loading('fail')
                return
            passed = True
            for proxy_congestion in proxy_congestions:
                if proxy_congestion.get('dead_congested') != 0 or proxy_congestion.get('server_state') not in server_state:
                    passed = False
                    break
            if passed:
                break
            else:
                time.sleep(3)
    stdio.stop_loading('succeed')

    # drop old tables
    bmsql_sql_path = pre_test_ret.get_return("bmsql_sql_path", '')
    run_sql(sql_file=os.path.join(bmsql_sql_path, 'tableDrops.sql'), force=True)

    if not merge(plugin_context, stdio, cursor, tenant_name):
        return False

    # create new tables
    if not run_sql(sql_file=os.path.join(bmsql_sql_path, 'tableCreates.sql')):
        stdio.error('Create tables failed')
        return False

    # load data
    stdio.verbose('Start to load data.')
    cmd = '{java_bin} -cp {cp} -Dprop={prop} LoadData'.format(java_bin=java_bin, cp=bmsql_classpath, prop=bmsql_prop_path)
    try:
        stdio.verbose('local execute: %s' % cmd)
        subprocess.call(cmd, shell=True, stderr=subprocess.STDOUT)
    except:
        stdio.exception('failed to load data')

    # create index
    stdio.start_loading('create index')
    if not run_sql(sql_file=os.path.join(bmsql_sql_path, 'indexCreates.sql')):
        stdio.error('Create index failed')
        stdio.stop_loading('fail')
        return
    stdio.stop_loading('succeed')

    # build finish
    stdio.start_loading('finish build')
    if not run_sql(sql_file=os.path.join(bmsql_sql_path, 'buildFinish.sql')):
        stdio.error('Finish build failed')
        stdio.stop_loading('fail')
        return
    stdio.stop_loading('succeed')

    # check result
    stdio.start_loading('check data')
    try:
        assert get_table_rows('bmsql_warehouse') == warehouses, Exception('warehouse num wrong')
        assert get_table_rows('bmsql_district') == warehouses * 10, Exception('district num wrong')
        stdio.stop_loading('succeed')
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.verbose(e)
        stdio.error('Check data failed.')
        return
    return plugin_context.return_true()
