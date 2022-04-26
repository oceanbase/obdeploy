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


stdio = None


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'([1-9][0-9]*)\s*([B,K,M,G,T])', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G']
    units_num = len(units) - 1
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
        limit = 1024
    else:
        div = 1024
        limit = 1024
        format = '%d%s'
    while idx < units_num and size >= limit:
        size /= div
        idx += 1
    return format % (size, units[idx])


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
    obclient_bin = get_option('obclient_bin', 'obclient')

    sql_path = sorted(sql_path, key=lambda x: (len(x), x))

    sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
    max_cpu = 2
    cpu_total = 0
    min_memory = 0
    unit_count = 0
    tenant_meta = None
    tenant_unit = None
    try:
        stdio.verbose('execute sql: %s' % (sql % tenant_name))
        cursor.execute(sql, [tenant_name])
        tenant_meta = cursor.fetchone()
        if not tenant_meta:
            stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
            return
        sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d" % tenant_meta['tenant_id']
        pool = execute(cursor, sql)
        sql = "select * from oceanbase.__all_unit_config where unit_config_id = %d" % pool['unit_config_id']
        tenant_unit = execute(cursor, sql)
        max_cpu = tenant_unit['max_cpu']
        min_memory = tenant_unit['min_memory']
        unit_count = pool['unit_count']
    except:
        stdio.error('fail to get tenant info')
        return

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

    sql = ''
    system_configs_done = []
    tenant_variables_done = []

    try:
        cache_wash_threshold = format_size(int(min_memory * 0.2), 0)
        system_configs = [
            # [配置名, 新值, 旧值, 替换条件: lambda n, o: n != o, 是否是租户级]
            ['syslog_level', 'PERF', 'PERF', lambda n, o: n != o, False],
            ['max_syslog_file_count', 100, 100, lambda n, o: n != o, False],
            ['enable_syslog_recycle', True, True, lambda n, o: n != o, False],
            ['enable_merge_by_turn', False, False, lambda n, o: n != o, False],
            ['trace_log_slow_query_watermark', '100s', '100s', lambda n, o: n != o, False],
            ['max_kept_major_version_number', 1, 1, lambda n, o: n != o, False],
            ['enable_sql_operator_dump', True, True, lambda n, o: n != o, False],
            ['_hash_area_size', '3g', '3g', lambda n, o: n != o, False],
            ['memstore_limit_percentage', 50, 50, lambda n, o: n != o, False],
            ['enable_rebalance', False, False, lambda n, o: n != o, False],
            ['memory_chunk_cache_size', '1g', '1g', lambda n, o: n != o, False],
            ['minor_freeze_times', 5, 5, lambda n, o: n != o, False],
            ['merge_thread_count', 20, 20, lambda n, o: n != o, False],
            ['cache_wash_threshold', cache_wash_threshold, cache_wash_threshold, lambda n, o: n != o, False],
            ['ob_enable_batched_multi_statement', True, True, lambda n, o: n != o, False],
        ]

        tenant_q = ' tenant="%s"' % tenant_name
        server_num = len(cluster_config.servers)
        if optimization:
            for config in system_configs:
                if config[0] == 'sleep':
                    time.sleep(config[1])
                    system_configs_done.append(config)
                    continue
                sql = 'show parameters like "%s"' % config[0]
                if config[4]:
                    sql += tenant_q
                ret = execute(cursor, sql)
                if ret:
                    config[2] = ret['value']
                    if config[3](config[1], config[2]):
                        sql = 'alter system set %s=%%s' % config[0]
                        if config[4]:
                            sql += tenant_q
                        system_configs_done.append(config)
                        execute(cursor, sql, [config[1]])

            sql = "select count(1) server_num from oceanbase.__all_server where status = 'active'"
            ret = execute(cursor, sql)
            if ret:
                server_num = ret.get("server_num", server_num)

            parallel_max_servers = min(int(max_cpu * 10), 1800)
            parallel_servers_target = int(max_cpu * server_num * 8)
            tenant_variables = [
                # [变量名, 新值, 旧值, 替换条件: lambda n, o: n != o]
                ['ob_sql_work_area_percentage', 80, 80, lambda n, o: n != o],
                ['optimizer_use_sql_plan_baselines', True, True, lambda n, o: n != o],
                ['optimizer_capture_sql_plan_baselines', True, True, lambda n, o: n != o],
                ['ob_query_timeout', 36000000000, 36000000000, lambda n, o: n != o],
                ['ob_trx_timeout', 36000000000, 36000000000, lambda n, o: n != o],
                ['max_allowed_packet', 67108864, 67108864, lambda n, o: n != o],
                ['secure_file_priv', "", "", lambda n, o: n != o],
                ['parallel_max_servers', parallel_max_servers, parallel_max_servers, lambda n, o: n != o],
                ['parallel_servers_target', parallel_servers_target, parallel_servers_target, lambda n, o: n != o]
            ]
            select_sql_t = "select value from oceanbase.__all_virtual_sys_variable where tenant_id = %d and name = '%%s'" % tenant_meta['tenant_id']
            update_sql_t = "ALTER TENANT %s SET VARIABLES %%s = %%%%s" % tenant_name

            for config in tenant_variables:
                sql = select_sql_t % config[0]
                ret = execute(cursor, sql)
                if ret:
                    value = ret['value']
                    config[2] = int(value) if isinstance(value, str) and value.isdigit() else value
                    if config[3](config[1], config[2]):
                        sql = update_sql_t % config[0]
                        tenant_variables_done.append(config)
                        execute(cursor, sql, [config[1]])
        else:
            sql = "select value from oceanbase.__all_virtual_sys_variable where tenant_id = %d and name = 'secure_file_priv'" % tenant_meta['tenant_id']
            ret = execute(cursor, sql)['value']
            if ret is None:
                stdio.error('Access denied. Please set `secure_file_priv` to "".')
                return
            if ret:
                for path in tbl_path:
                    if not path.startswith(ret):
                        stdio.error('Access denied. Please set `secure_file_priv` to "".')
                        return

        parallel_num = int(max_cpu * unit_count)
        
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
                ret = local_execute_command("""%s -c -e "load data /*+ parallel(%s) */ infile '%s' into table %s fields terminated by '|';" """ % (sql_cmd_prefix, parallel_num, path, fn[:-4]))
                if not ret:
                    raise Exception(ret.stderr)
            stdio.stop_loading('succeed')

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
            ret = local_execute_command('source %s | %s -c > %s' % (path, sql_cmd_prefix, log_path))
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
            stdio.print('[%s]: end %s, cost %.1fs' % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)), path, cost))
            if not ret:
                raise Exception(ret.stderr)
        stdio.print('Total Cost: %.1fs' % total_cost)

    except KeyboardInterrupt:
        stdio.stop_loading('fail')
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.exception(str(e))
    finally:
        try:
            if optimization:
                for config in tenant_variables_done[::-1]:
                    if config[3](config[1], config[2]):
                        sql = update_sql_t % config[0]
                        execute(cursor, sql, [config[2]])

                for config in system_configs_done[::-1]:
                    if config[0] == 'sleep':
                        time.sleep(config[1])
                        continue
                    if config[3](config[1], config[2]):
                        sql = 'alter system set %s=%%s' % config[0]
                        if config[4]:
                            sql += tenant_q
                        execute(cursor, sql, [config[2]])
        except:
            pass
