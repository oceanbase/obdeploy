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
from tool import get_option


def run_test(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options

    pre_test_ret = plugin_context.get_return("pre_test")

    bmsql_jar = get_option(options, 'bmsql_jar')
    bmsql_libs = get_option(options, 'bmsql_libs')
    bmsql_classpath = pre_test_ret.get_return("bmsql_classpath")
    if not bmsql_classpath:
        jars = [bmsql_jar]
        jars.extend(bmsql_libs.split(','))
        bmsql_classpath = ':'.join(jars)
    bmsql_prop_path = pre_test_ret.get_return('bmsql_prop_path')
    stdio.verbose('get bmsql_prop_path: {}'.format(bmsql_prop_path))
    run_path = pre_test_ret.get_return('run_path')
    host = get_option(options, 'host', '127.0.0.1')
    db_name = get_option(options, 'database', 'test')
    user = get_option(options, 'user', 'root')
    password = get_option(options, 'password', '')
    tenant_name = get_option(options, 'tenant', 'test')
    obclient_bin = get_option(options, 'obclient_bin', 'obclient')
    run_mins = get_option(options, 'run_mins', 10)
    java_bin = get_option(options, 'java_bin', 'java')

    sys_namespace = kwargs.get("sys_namespace")
    get_db_and_cursor = kwargs.get("get_db_and_cursor")
    db, cursor = get_db_and_cursor(sys_namespace)
    port = db.port if db else 2881

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

    merge_version = cursor.fetchone("select value from oceanbase.__all_zone where name='frozen_version'")
    if merge_version is False:
        return
    merge_version = merge_version['value']
    stdio.start_loading('Merge')
    if cursor.fetchone('alter system major freeze') is False:
        return
    sql = "select value from oceanbase.__all_zone where name='frozen_version' and value != %s" % merge_version
    while True:
        res = cursor.fetchone(sql)
        if res is False:
            return
        if res:
            break
        time.sleep(1)

    while True:
        res = cursor.fetchone("""select * from  oceanbase.__all_zone 
                                 where name='last_merged_version'
                                 and value != (select value from oceanbase.__all_zone where name='frozen_version' limit 1)
                                 and zone in (select zone from  oceanbase.__all_zone where name='status' and info = 'ACTIVE')
                              """)
        if res is False:
            return
        if not res:
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
                ret = LocalClient.execute_command("tail -c 1000 %s" % log_path, stdio=stdio)
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
