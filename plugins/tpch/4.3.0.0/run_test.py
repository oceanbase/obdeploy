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


import re
import os
import time

try:
    import subprocess32 as subprocess
except:
    import subprocess
from ssh import LocalClient
from tool import FileUtil


stdio = None


def exec_cmd(cmd):
    stdio.verbose('execute: %s' % cmd)
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while process.poll() is None:
        line = process.stdout.readline()
        line = line.strip()
        if line:
            stdio.print(line.decode("utf8", 'ignore'))
    return process.returncode == 0


def run_test(plugin_context, db, cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    global stdio
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    options = plugin_context.options

    optimization = get_option('optimization') > 0
    not_test_only = not get_option('test_only')

    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    mysql_db = get_option('database', 'test')
    user = get_option('user', 'root')
    tenant_name = get_option('tenant', 'test')
    password = get_option('password', '')
    ddl_path = get_option('ddl_path')
    tbl_path = get_option('tbl_path')
    sql_path = get_option('sql_path')
    tmp_dir = get_option('tmp_dir')
    direct_load = get_option('direct_load')
    input_parallel = get_option('parallel')
    obclient_bin = get_option('obclient_bin', 'obclient')

    sql_path = sorted(sql_path, key=lambda x: (len(x), x))

    cpu_total = 0
    max_cpu = kwargs.get('max_cpu', 2)
    tenant_id = kwargs.get('tenant_id')
    unit_count = kwargs.get('unit_count', 0)
    memory_size = kwargs.get('memory_size', kwargs.get('min_memory'))
    if not_test_only:
        sql_cmd_prefix = '%s -h%s -P%s -u%s@%s %s -A' % (obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '')
        ret = local_execute_command('%s -e "%s"' % (sql_cmd_prefix, 'create database if not exists %s' % mysql_db))
        sql_cmd_prefix += ' -D %s' % mysql_db
        if not ret:
            stdio.error(ret.stderr)
            return
    else:
        sql_cmd_prefix = '%s -h%s -P%s -u%s@%s %s -D %s -A' % (obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', mysql_db)

    ret = LocalClient.execute_command('%s -e "%s"' % (sql_cmd_prefix, 'select version();'), stdio=stdio)
    if not ret:
        stdio.error(ret.stderr)
        return

    for server in cluster_config.servers:
        client = clients[server]
        ret = client.execute_command("grep -e 'processor\s*:' /proc/cpuinfo | wc -l")
        if ret and ret.stdout.strip().isdigit():
            cpu_total += int(ret.stdout)
        else:
            server_config = cluster_config.get_server_conf(server)
            cpu_total += int(server_config.get('cpu_count', 0))

    try:
        sql = "select value from oceanbase.__all_virtual_sys_variable where tenant_id = %d and name = 'secure_file_priv'" % tenant_id
        ret = cursor.fetchone(sql)
        if ret is False:
            return
        ret = ret['value']
        if ret is None:
            stdio.error('Access denied. Please set `secure_file_priv` to "\\".')
            return
        if ret:
            for path in tbl_path:
                if not path.startswith(ret):
                    stdio.error('Access denied. Please set `secure_file_priv` to "\\".')
                    return
        if input_parallel:
            parallel_num = input_parallel
        else:
            if direct_load:
                parallel_num = int(((memory_size) >> 20) * 0.001) / 2 if memory_size else 1
            else:
                parallel_num = int(max_cpu * unit_count)
            parallel_num = max(parallel_num, 1)

        if not_test_only:
            # 替换并发数
            stdio.start_loading('Format DDL')
            n_ddl_path = []
            for fp in ddl_path:
                _, fn = os.path.split(fp)
                nfp = os.path.join(tmp_dir, fn)
                ret = local_execute_command("sed %s -e 's/partitions cpu_num/partitions %d/' > %s" % (fp, cpu_total, nfp))
                if not ret:
                    raise Exception(ret.stderr)
                n_ddl_path.append(nfp)
            ddl_path = n_ddl_path
            stdio.stop_loading('succeed')

            stdio.start_loading('Create table')
            for path in ddl_path:
                path = os.path.abspath(path)
                stdio.verbose('load %s' % path)
                ret = local_execute_command('%s < %s' % (sql_cmd_prefix, path))
                if not ret:
                    raise Exception(ret.stderr)
            stdio.stop_loading('succeed')

            stdio.start_loading('Load data')
            for path in tbl_path:
                _, fn = os.path.split(path)
                stdio.verbose('load %s' % path)
                ret = local_execute_command("""%s -c -e "load data /*+ parallel(%d) %s */ infile '%s' %s into table %s fields terminated by '|' enclosed BY ''ESCAPED BY'';" """ % (sql_cmd_prefix, parallel_num, 'direct(true, 0)' if direct_load else '', path, 'ignore' if direct_load else '', fn[:-4]))
                if not ret:
                    raise Exception(ret.stderr)
            stdio.stop_loading('succeed')

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
            local_dir, _ = os.path.split(__file__)
            analyze_path = os.path.join(local_dir, 'analyze.sql')
            with FileUtil.open(analyze_path, stdio=stdio) as f:
                content = f.read()
            analyze_content = content.format(cpu_total=cpu_total, database=mysql_db)
            ret = LocalClient.execute_command('%s -e """%s"""' % (sql_cmd_prefix, analyze_content), stdio=stdio)
            if not ret:
                raise Exception(ret.stderr)
            stdio.stop_loading('succeed')

        # 替换并发数
        stdio.start_loading('Format SQL')
        n_sql_path = []
        for fp in sql_path:
            _, fn = os.path.split(fp)
            nfp = os.path.join(tmp_dir, fn)
            ret = local_execute_command("sed %s -e 's/parallel(cpu_num)/parallel(%d)/' > %s" % (fp, cpu_total, nfp))
            if not ret:
                raise Exception(ret.stderr)
            n_sql_path.append(nfp)
        sql_path = n_sql_path
        stdio.stop_loading('succeed')

        #warmup预热
        stdio.start_loading('Warmup')
        times = 2
        for path in sql_path:
            _, fn = os.path.split(path)
            log_path = os.path.join(tmp_dir, '%s.log' % fn)
            ret = local_execute_command('echo source %s | %s -c > %s' % (path, sql_cmd_prefix, log_path))
            if not ret:
                raise Exception(ret.stderr)
        stdio.stop_loading('succeed')

        total_cost = 0
        for path in sql_path:
            start_time = time.time()
            _, fn = os.path.split(path)
            log_path = os.path.join(tmp_dir, '%s.log' % fn)
            stdio.print('[%s]: start %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)), path))
            ret = local_execute_command('echo source %s | %s -c > %s' % (path, sql_cmd_prefix, log_path))
            end_time = time.time()
            cost = end_time - start_time
            total_cost += cost
            stdio.print('[%s]: end %s, cost %.2fs' % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)), path, cost))
            if not ret:
                raise Exception(ret.stderr)
        stdio.print('Total Cost: %.2fs' % total_cost)
        return plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.stop_loading('fail')
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.exception(str(e))
