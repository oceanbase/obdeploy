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
from collections import OrderedDict
from ssh import LocalClient
from tool import FileUtil

stdio = None


def run_test(plugin_context, cursor, odp_cursor=None, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

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
    tmp_dir = kwargs.get("tmp_dir")
    warehouses = kwargs.get("warehouses")
    terminals = kwargs.get("terminals")
    cpu_total = kwargs.get('cpu_total')

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

    tenant_id = kwargs.get('tenant_id')

    # Major freeze
    stdio.start_loading('Merge')
    sql_frozen_scn = "select FROZEN_SCN, LAST_SCN from oceanbase.CDB_OB_MAJOR_COMPACTION where tenant_id = %s" % tenant_id
    merge_version = cursor.fetchone(sql_frozen_scn)
    if merge_version is False:
        return
    merge_version = merge_version['FROZEN_SCN']
    if cursor.fetchone("alter system major freeze tenant = %s" % tenant_name) is False:
        return
    while True:
        current_version = cursor.fetchone(sql_frozen_scn)
        if current_version is False:
            return
        current_version = current_version['FROZEN_SCN']
        if int(current_version) > int(merge_version):
            break
        time.sleep(5)
    while True:
        ret = cursor.fetchone(sql_frozen_scn)
        if ret is False:
            return
        if int(ret.get("FROZEN_SCN", 0)) / 1000 == int(ret.get("LAST_SCN", 0)) / 1000:
            break
        time.sleep(5)
    # analyze
    ret = LocalClient.execute_command("%s \"show parameters where name = 'enable_sql_extension' \G;\"" % exec_sql_cmd, stdio=stdio)
    if ret:
        output = ret.stdout.strip()
        searched = re.search('\s+value:\s+(\S+)\n', output)
        if searched:
            value = searched.group(1).lower()
            if value == 'true':
                local_dir, _ = os.path.split(__file__)
                analyze_path = os.path.join(local_dir, 'analyze.sql')
                with FileUtil.open(analyze_path, stdio=stdio) as f:
                    content = f.read()
                analyze_content = content.format(cpu_total=cpu_total, database=db_name)
                ret = LocalClient.execute_command('%s """%s"""' % (exec_sql_cmd, analyze_content), stdio=stdio)
                if not ret:
                    stdio.error('failed to analyze table: {}'.format(ret.stderr))
                    stdio.stop_loading('fail')
                    return
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
    cmd = '{java_bin} -cp {cp} -Dprop={prop} -DrunID={seq} jTPCC 2>&1 | tee {output}'.format(
        java_bin=java_bin,
        run_path=run_path,
        cp=bmsql_classpath, prop=bmsql_prop_path, seq=seq, output=log_path)
    try:
        stdio.verbose('local execute: %s' % cmd)
        subprocess.call(cmd, shell=True, stderr=subprocess.STDOUT, cwd=run_path)
        with open(log_path, 'r') as f:
            out = f.read()
        stdio.verbose('stdout: %s' % out)
        output = 'TPC-C Result\n'
        key_map = OrderedDict({
            r'Measured tpmC \(NewOrders\)': "tpmc",
            r'Measured tpmTOTAL': "tpmtotal",
            r'Session Start': "start_time",
            r'Session End': "end_time",
            r'Transaction Count': "trans_count"
        })
        max_length = max([len(x) for x in key_map])
        args = {
            'report_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'warehouses': warehouses,
            'terminals': terminals,
            'run_mins': run_mins
        }
        for k in key_map:
            matched = re.match(r'.*(%s)\s+=\s+(.*?)\n' % k, out, re.S)
            if not matched:
                stdio.error('Failed to run TPC-C benchmark.')
                return
            value = matched.group(2)
            key = matched.group(1)
            key = key + " " * (max_length - len(key))
            output += '{} : {}\n'.format(key, value)
            args[key_map[k]] = value
        stdio.print(output)
        # # html测试报告
        # try:
        #     tpcc_path = os.path.join(tmp_dir, 'tpcc.html')
        #     tmp_path = os.path.join(tmp_dir, 'tpcc.html')
        #     with open(tmp_path, "r", encoding='UTF-8') as h:
        #         TPCC_TEMPLATE = h.read().replace('%2', '%')
        #     with open(tpcc_path, 'w') as f:
        #         f.write(TPCC_TEMPLATE.replace('%', '%%').replace('%%(', '%(') % args)
        # except Exception as e:
        #     stdio.exception(e)
        #     stdio.error('Failed to generate html report for tpcc.')
        #     stdio.stop_loading('fail')
        #     return
        # return plugin_context.return_true()
    except Exception as e:
        error = str(e)
        verbose_msg = 'exited code 255, error output:\n%s' % error
        stdio.verbose(verbose_msg)
        stdio.exception('')