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

try:
    import subprocess32 as subprocess
except:
    import subprocess
import os
import time
import re

from ssh import LocalClient
from _errno import EC_TPCC_LOAD_DATA_FAILED


def build(plugin_context, cursor, odp_cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        stdio.verbose('get option: {} value {}'.format(key, value))
        return value

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    def execute(cursor, query, args=None):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose('execute sql: %s' % msg)
        stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            cursor.execute(query, args)
            return cursor.fetchone()
        except:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    def run_sql(sql_file, force=False):
        sql_cmd = "{obclient} -h{host} -P{port} -u{user}@{tenant} {password_arg} -A {db} {force_flag} < {sql_file}".format(
            obclient=obclient_bin, host=host, port=port, user=user, tenant=tenant_name,
            password_arg=("-p'%s'" % password) if password else '',
            db=db_name,
            force_flag='-f' if force else '',
            sql_file=sql_file)
        return local_execute_command(sql_cmd)

    def get_table_rows(table_name):
        table_rows = 0
        ret = local_execute_command('%s "%s" -E' % (exec_sql_cmd, 'select count(*) from %s' % table_name))
        matched = re.match(r'.*count\(\*\):\s?(\d+)', ret.stdout, re.S)
        if matched:
            table_rows = int(matched.group(1))
        return table_rows

    stdio = plugin_context.stdio
    options = plugin_context.options

    bmsql_jar = get_option('bmsql_jar')
    bmsql_libs = get_option('bmsql_libs')

    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    db_name = get_option('database', 'test')
    user = get_option('user', 'root')
    password = get_option('password', '')
    tenant_name = get_option('tenant', 'test')
    obclient_bin = get_option('obclient_bin', 'obclient')
    java_bin = get_option('java_bin', 'java')

    bmsql_classpath = kwargs.get('bmsql_classpath')
    if not bmsql_classpath:
        jars = [bmsql_jar]
        jars.extend(bmsql_libs.split(','))
        bmsql_classpath = '.:' + ':'.join(jars)
    bmsql_prop_path = kwargs.get('bmsql_prop_path')
    stdio.verbose('get bmsql_prop_path: {}'.format(bmsql_prop_path))
    warehouses = kwargs.get('warehouses', 0)

    stdio.verbose('Check connect ready')
    exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A %s -e" % (
        obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', db_name)
    stdio.start_loading('Connect to tenant %s' % tenant_name)
    try:
        while True:
            ret = local_execute_command('%s "%s" -E' % (exec_sql_cmd, 'select version();'))
            if ret:
                break
            time.sleep(10)
        stdio.stop_loading('succeed')
    except:
        stdio.stop_loading('fail')
        stdio.exception('')
        return
    stdio.start_loading('Server check')
    try:
        # check for observer
        while True:
            sql = "select * from oceanbase.__all_server where status != 'active' or stop_time > 0 or start_service_time = 0"
            stdio.verbose('execute sql: %s' % sql)
            cursor.execute(sql)
            ret = cursor.fetchone()
            if ret is None:
                break
            time.sleep(3)
        # check for obproxy
        if odp_cursor:
            while True:
                sql = "show proxycongestion all"
                stdio.verbose('execute obproxy sql: %s' % sql)
                odp_cursor.execute(sql)
                proxy_congestions = odp_cursor.fetchall()
                passed = True
                for proxy_congestion in proxy_congestions:
                    if proxy_congestion.get('dead_congested') != 0 or proxy_congestion.get('server_state') != 'ACTIVE':
                        passed = False
                        break
                if passed:
                    break
                else:
                    time.sleep(3)
    except:
        stdio.stop_loading('fail')
        stdio.exception('')
        return
    stdio.stop_loading('succeed')

    # drop old tables
    bmsql_sql_path = kwargs.get('bmsql_sql_path', '')
    run_sql(sql_file=os.path.join(bmsql_sql_path, 'tableDrops.sql'), force=True)

    merge_version = execute(cursor, "select value from oceanbase.__all_zone where name='frozen_version'")['value']
    stdio.start_loading('Merge')
    execute(cursor, 'alter system major freeze')
    sql = "select value from oceanbase.__all_zone where name='frozen_version' and value != %s" % merge_version
    while True:
        if execute(cursor, sql):
            break
        time.sleep(1)

    while True:
        if not execute(cursor, """select * from  oceanbase.__all_zone 
                        where name='last_merged_version'
                        and value != (select value from oceanbase.__all_zone where name='frozen_version' limit 1)
                        and zone in (select zone from  oceanbase.__all_zone where name='status' and info = 'ACTIVE')
                        """):
            break
        time.sleep(5)
    stdio.stop_loading('succeed')

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
