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
from time import sleep
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
        formate = '%.' + str(precision) + 'f%s'
        limit = 1024
    else:
        div = 1024
        limit = 1024
        formate = '%d%s'
    while idx < units_num and size >= limit:
        size /= div
        idx += 1
    return formate % (size, units[idx])


def exec_cmd(cmd):
    stdio.verbose('execute: %s' % cmd)
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while process.poll() is None:
        line = process.stdout.readline()
        line = line.strip()
        if line:
            stdio.print(line.decode("utf8", 'ignore'))
    return process.returncode == 0


def run_test(plugin_context, db, cursor, odp_db, odp_cursor=None, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if not value:
            value = default
        return value
    def execute(cursor, query, args=None):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose('execute sql: %s' % msg)
        # stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            cursor.execute(query, args)
            return cursor.fetchone()
        except:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    global stdio
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    options = plugin_context.options

    optimization = get_option('optimization', 1) > 0

    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    mysql_db = get_option('database', 'test')
    user = get_option('user', 'root')
    tenant_name = get_option('tenant', 'test')
    password = get_option('password', '')
    table_size = get_option('table_size', 10000)
    tables = get_option('tables', 32)
    threads = get_option('threads', 150)
    time = get_option('time', 60)
    interval = get_option('interval', 10)
    events = get_option('events', 0)
    rand_type = get_option('rand_type', None)
    skip_trx = get_option('skip_trx', '').lower()
    percentile = get_option('percentile', None)
    script_name = get_option('script_name', 'point_select.lua')
    obclient_bin = get_option('obclient_bin', 'obclient')
    sysbench_bin = get_option('sysbench_bin', 'sysbench')
    sysbench_script_dir = get_option('sysbench_script_dir', '/usr/sysbench/share/sysbench')

    ret = LocalClient.execute_command('%s --help' % obclient_bin, stdio=stdio)
    if not ret:
        stdio.error('%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (ret.stderr, obclient_bin))
        return
    ret = LocalClient.execute_command('%s --help' % sysbench_bin, stdio=stdio)
    if not ret:
        stdio.error('%s\n%s is not an executable file. Please use `--sysbench-bin` to set.\nYou may not have ob-sysbench installed' % (ret.stderr, sysbench_bin))
        return

    if not script_name.endswith('.lua'):
        script_name += '.lua'
    script_path = os.path.join(sysbench_script_dir, script_name)
    if not os.path.exists(script_path):
        stdio.error('No such file %s. Please use `--sysbench-script-dir` to set sysbench scrpit dir.\nYou may not have ob-sysbench installed' % script_path)
        return

    sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
    max_cpu = 2
    tenant_meta = None
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
        max_cpu = execute(cursor, sql)['max_cpu']
    except:
        return

    sql = "select * from oceanbase.__all_user where user_name = %s"
    try:
        stdio.verbose('execute sql: %s' % (sql % user))
        cursor.execute(sql, [user])
        if not cursor.fetchone():
            stdio.error('User %s not exists.' % user)
            return
    except:
        return

    exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A -e" % (obclient_bin, host, port, user, tenant_name, "-p'%s'" if password else '')
    ret = LocalClient.execute_command('%s "%s"' % (exec_sql_cmd, 'select version();'), stdio=stdio)
    if not ret:
        stdio.error(ret.stderr)
        return

    sql = ''
    odp_configs = [
        # [配置名, 新值, 旧值, 替换条件: lambda n, o: n != o]
        ['enable_compression_protocol', False, False, lambda n, o: n != o],
        ['proxy_mem_limited', format_size(min(max(threads * (8 << 10), 2 << 30), 4 << 30), 0), 0, lambda n, o: parse_size(n) > parse_size(o)],
        ['enable_prometheus', False, False, lambda n, o: n != o],
        ['enable_metadb_used', False, False, lambda n, o: n != o],
        ['enable_standby', False, False, lambda n, o: n != o],
        ['enable_strict_stat_time', False, False, lambda n, o: n != o],
        ['use_local_dbconfig', True, True, lambda n, o: n != o],
    ]
    system_configs = [
        # [配置名, 新值, 旧值, 替换条件: lambda n, o: n != o, 是否是租户级]
        ['enable_auto_leader_switch', False, False, lambda n, o: n != o, False],
        ['enable_one_phase_commit', False, False, lambda n, o: n != o, False],
        ['weak_read_version_refresh_interval', '5s', '5s', lambda n, o: n != o, False],
        ['syslog_level', 'PERF', 'PERF', lambda n, o: n != o, False],
        ['max_syslog_file_count', 100, 100, lambda n, o: n != o, False],
        ['enable_syslog_recycle', True, True, lambda n, o: n != o, False],
        ['trace_log_slow_query_watermark', '10s', '10s', lambda n, o: n != o, False],
        ['large_query_threshold', '1s', '1s', lambda n, o: n != o, False],
        ['clog_sync_time_warn_threshold', '200ms', '200ms', lambda n, o: n != o, False],
        ['syslog_io_bandwidth_limit', '10M', '10M', lambda n, o: n != o, False],
        ['enable_sql_audit', False, False, lambda n, o: n != o, False],
        ['sleep', 1],
        ['enable_perf_event', False, False, lambda n, o: n != o, False],
        ['clog_max_unconfirmed_log_count', 5000, 5000, lambda n, o: n != o, False],
        ['autoinc_cache_refresh_interval', '86400s', '86400s', lambda n, o: n != o, False],
        ['enable_early_lock_release', False, False, lambda n, o: n != o, True],
        ['default_compress_func', 'lz4_1.0', 'lz4_1.0', lambda n, o: n != o, False],
        ['_clog_aggregation_buffer_amount', 4, 4, lambda n, o: n != o, False],
        ['_flush_clog_aggregation_buffer_timeout', '1ms', '1ms', lambda n, o: n != o, False],
    ]

    if odp_cursor and optimization:
        try:
            for config in odp_configs:
                sql = 'show proxyconfig like "%s"' % config[0]
                ret = execute(odp_cursor, sql)
                if ret:
                    config[2] = ret['value']
                    if config[3](config[1], config[2]):
                        sql = 'alter proxyconfig set %s=%%s' % config[0]
                        execute(odp_cursor, sql, [config[1]])
        except:
            return

    tenant_q = ' tenant="%s"' % tenant_name
    server_num = len(cluster_config.servers)
    if optimization:
        try:
            for config in system_configs:
                if config[0] == 'sleep':
                    sleep(config[1])
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
                        execute(cursor, sql, [config[1]])

            sql = "select count(1) server_num from oceanbase.__all_server where status = 'active'"
            ret = execute(cursor, sql)
            if ret:
                server_num = ret.get("server_num", server_num)
        except:
            return

        parallel_max_servers = max_cpu * 10
        parallel_servers_target = int(parallel_max_servers * server_num * 0.8)

        tenant_variables = [
            # [变量名, 新值, 旧值, 替换条件: lambda n, o: n != o]
            ['ob_timestamp_service', 1, 1, lambda n, o: n != o],
            ['autocommit', 1, 1, lambda n, o: n != o],
            ['ob_query_timeout', 36000000000, 36000000000, lambda n, o: n != o],
            ['ob_trx_timeout', 36000000000, 36000000000, lambda n, o: n != o],
            ['max_allowed_packet', 67108864, 67108864, lambda n, o: n != o],
            ['ob_sql_work_area_percentage', 100, 100, lambda n, o: n != o],
            ['parallel_max_servers', parallel_max_servers, parallel_max_servers, lambda n, o: n != o],
            ['parallel_servers_target', parallel_servers_target, parallel_servers_target, lambda n, o: n != o]
        ]
        select_sql_t = "select value from oceanbase.__all_virtual_sys_variable where tenant_id = %d and name = '%%s'" % tenant_meta['tenant_id']
        update_sql_t = "ALTER TENANT %s SET VARIABLES %%s = %%%%s" % tenant_name

        try:
            for config in tenant_variables:
                sql = select_sql_t % config[0]
                ret = execute(cursor, sql)
                if ret:
                    value = ret['value']
                    config[2] = int(value) if isinstance(value, str) or value.isdigit() else value
                    if config[3](config[1], config[2]):
                        sql = update_sql_t % config[0]
                        execute(cursor, sql, [config[1]])
        except:
            return

    sysbench_cmd = "cd %s; %s %s --mysql-host=%s --mysql-port=%s --mysql-user=%s@%s --mysql-db=%s" % (sysbench_script_dir, sysbench_bin, script_name, host, port, user, tenant_name, mysql_db)

    if password:
        sysbench_cmd += ' --mysql-password=%s' % password
    if table_size:
        sysbench_cmd += ' --table_size=%s' % table_size
    if tables:
        sysbench_cmd += ' --tables=%s' % tables
    if threads:
        sysbench_cmd += ' --threads=%s' % threads
    if time:
        sysbench_cmd += ' --time=%s' % time
    if interval:
        sysbench_cmd += ' --report-interval=%s' % interval
    if events:
        sysbench_cmd += ' --events=%s' % events
    if rand_type:
        sysbench_cmd += ' --rand-type=%s' % rand_type
    if skip_trx in ['on', 'off']:
        sysbench_cmd += ' --skip_trx=%s' % skip_trx
    if percentile:
        sysbench_cmd += ' --percentile=%s' % percentile

    try:
        if exec_cmd('%s cleanup' % sysbench_cmd) and exec_cmd('%s prepare' % sysbench_cmd) and exec_cmd('%s --db-ps-mode=disable run' % sysbench_cmd):
            return plugin_context.return_true()
    except KeyboardInterrupt:
        pass
    except:
        stdio.exception('')
    finally:
        try:
            if optimization:
                for config in tenant_variables[::-1]:
                    if config[3](config[1], config[2]):
                        sql = update_sql_t % config[0]
                        execute(cursor, sql, [config[2]])

                for config in system_configs[::-1]:
                    if config[0] == 'sleep':
                        sleep(config[1])
                        continue
                    if config[3](config[1], config[2]):
                        sql = 'alter system set %s=%%s' % config[0]
                        if config[4]:
                            sql += tenant_q
                        execute(cursor, sql, [config[2]])

                if odp_cursor:
                    for config in odp_configs[::-1]:
                        if config[3](config[1], config[2]):
                            sql = 'alter proxyconfig set %s=%%s' % config[0]
                            execute(odp_cursor, sql, [config[2]])
        except:
            pass
