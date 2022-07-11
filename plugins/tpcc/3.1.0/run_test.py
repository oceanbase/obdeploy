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

import datetime
import os
import re
import time

try:
    import subprocess32 as subprocess
except:
    import subprocess

from ssh import LocalClient
from _errno import EC_TPCC_RUN_TEST_FAILED

stdio = None


def run_test(plugin_context, cursor, odp_cursor=None, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

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

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    global stdio
    stdio = plugin_context.stdio
    options = plugin_context.options
    bmsql_jar = get_option('bmsql_jar')
    bmsql_libs = get_option('bmsql_libs')
    bmsql_classpath = kwargs.get('bmsql_classpath')
    if not bmsql_classpath:
        jars = [bmsql_jar]
        jars.extend(bmsql_libs.split(','))
        bmsql_classpath = ':'.join(jars)
    bmsql_prop_path = kwargs.get('bmsql_prop_path')
    stdio.verbose('get bmsql_prop_path: {}'.format(bmsql_prop_path))
    run_path = kwargs.get('run_path')
    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    db_name = get_option('database', 'test')
    user = get_option('user', 'root')
    password = get_option('password', '')
    tenant_name = get_option('tenant', 'test')
    obclient_bin = get_option('obclient_bin', 'obclient')
    run_mins = get_option('run_mins', 10)
    java_bin = get_option('java_bin', 'java')

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

    stdio.verbose('Benchmark run')
    seq_file = os.path.join(run_path, '.jTPCC_run_seq.dat')
    try:
        with open(seq_file) as f:
            seq = int(f.read())
    except Exception as e:
        stdio.verbose(e)
        seq = 0
    seq += 1
    with open(seq_file, 'w') as f:
        f.write(str(seq))
    log_path = os.path.join(run_path, 'tpcc_out_{}_{}'.format(seq, datetime.datetime.now().strftime('%Y%m%d%H%M%S')))
    cmd = '{java_bin} -cp {cp} -Dprop={prop} -DrunID={seq} jTPCC'.format(
        java_bin=java_bin,
        run_path=run_path,
        cp=bmsql_classpath, prop=bmsql_prop_path, seq=seq)
    try:
        stdio.verbose('local execute: %s' % cmd)
        with open(log_path, 'wb', 0) as logf:
            p = subprocess.Popen(cmd, shell=True, stdout=logf, stderr=subprocess.STDOUT, cwd=run_path)
            stdio.start_loading('Benchmark run')
            start_time = datetime.datetime.now()
            timeout = datetime.timedelta(seconds=int(run_mins * 60 * 1.2))
            while p.poll() is None:
                time.sleep(1)
                ret = local_execute_command("tail -c 1000 %s" % log_path)
                if ret:
                    stdio.update_loading_text(ret.stdout.strip('\b\r\n ').split('\n')[-1].split('\b')[-1].strip())
                if datetime.datetime.now() - start_time > timeout:
                    p.terminate()
                    stdio.verbose('Run benchmark sql timeout.')
                    stdio.error(EC_TPCC_RUN_TEST_FAILED)
                    stdio.verbose('return code: {}'.format(p.returncode))
                    with open(log_path, 'r') as f:
                        out = f.read()
                    stdio.verbose('output: {}'.format(out))
                    return
            stdio.update_loading_text('Benchmark run')
        code = p.returncode
        with open(log_path, 'r') as f:
            out = f.read()
        verbose_msg = 'exited code %s' % code
        if code:
            verbose_msg += ', output: %s' % out
            stdio.verbose(verbose_msg)
            stdio.error(EC_TPCC_RUN_TEST_FAILED)
            stdio.stop_loading('fail')
            return
        stdio.verbose('stdout: %s' % out)
        output = 'TPC-C Result\n'
        for k in [r'Measured tpmC \(NewOrders\)', r'Measured tpmTOTAL', r'Session Start', r'Session End',
                  r'Transaction Count']:
            matched = re.match(r'.*(%s)\s+=\s+(.*?)\n' % k, out, re.S)
            if not matched:
                stdio.error(EC_TPCC_RUN_TEST_FAILED)
                return
            output += '{} : {}\n'.format(matched.group(1), matched.group(2))
        stdio.print(output)
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    except Exception as e:
        error = str(e)
        verbose_msg = 'exited code 255, error output:\n%s' % error
        stdio.verbose(verbose_msg)
        stdio.exception('')
        stdio.stop_loading('fail')
