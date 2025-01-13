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

from time import sleep

from ssh import LocalClient


def optimize(plugin_context, cursor, odp_cursor, *args, **kwargs):
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
        except Exception:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    def type_transform(expect, current):
        expect_type = type(expect)
        if isinstance(current, expect_type):
            return expect, current
        elif isinstance(current, (int, float)) or str(current).isdigit():
            return expect, expect_type(current)
        else:
            return str(expect).lower(), str(current).lower()

    global stdio
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    options = plugin_context.options
    optimization = get_option('optimization')
    ob_optimization = get_option('ob_optimization')
    not_test_only = not get_option('test_only')
    tenant_name = get_option('tenant', 'test')
    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    mysql_db = get_option('database', 'test')
    user = get_option('user', 'root')
    password = get_option('password', '')
    obclient_bin = get_option('obclient_bin', 'obclient')

    optimization_step = kwargs.get('optimization_step', 'build')
    success = False
    stdio.start_loading('Optimize for %s' % ('performance' if optimization_step == 'test' else 'server'))
    if optimization_step == 'test':
        exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A %s -e" % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', mysql_db)
        stdio.start_loading('Connect to tenant %s' % tenant_name)
        try:
            while True:
                ret = local_execute_command('%s "%s" -E' % (exec_sql_cmd, 'select version();'))
                if ret:
                    break
                sleep(10)
            stdio.stop_loading('succeed')
        except:
            stdio.stop_loading('fail')
            stdio.exception('')
            return
    sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
    try:
        stdio.verbose('execute sql: %s' % (sql % tenant_name))
        cursor.execute(sql, [tenant_name])
        tenant_meta = cursor.fetchone()
        if not tenant_meta:
            stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
            return
    except Exception as e:
        stdio.verbose(e)
        stdio.error('Fail to get tenant info')
        stdio.stop_loading('fail')
        return

    if not_test_only:
        sql_cmd_prefix = '%s -h%s -P%s -u%s@%s %s -A' % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '')
        ret = local_execute_command('%s -e "%s"' % (sql_cmd_prefix, 'create database if not exists %s' % mysql_db))
        sql_cmd_prefix += ' -D %s' % mysql_db
        if not ret:
            stdio.error(ret.stderr)
            stdio.stop_loading('fail')
            return
    else:
        sql_cmd_prefix = '%s -h%s -P%s -u%s@%s %s -D %s -A' % (
            obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '', mysql_db)

    ret = LocalClient.execute_command('%s -e "%s"' % (sql_cmd_prefix, 'select version();'), stdio=stdio)
    if not ret:
        stdio.error(ret.stderr)
        stdio.stop_loading('fail')
        return

    odp_configs_done = kwargs.get('odp_configs_done', [])
    system_configs_done = kwargs.get('system_configs_done', [])
    tenant_variables_done = kwargs.get('tenant_variables_done', [])
    odp_need_reboot = False
    obs_need_reboot = False
    variables_count_before = len(odp_configs_done) + len(system_configs_done) + len(tenant_variables_done)

    odp_configs_build = [
        # [配置名, 新值, 旧值, 替换条件: lambda n, o: n != o, 重启生效]
        # ['enable_strict_kernel_release', False, False, lambda n, o: n != o, True],
        ['automatic_match_work_thread', False, False, lambda n, o: n != o, True],
        ['proxy_mem_limited', '4G', '4G', lambda n, o: n != o, False],
        ['enable_compression_protocol', False, False, lambda n, o: n != o, True],
        ['slow_proxy_process_time_threshold', '500ms', '500ms', lambda n, o: n != o, False],
        ['enable_ob_protocol_v2', False, False, lambda n, o: n != o, True],
        ['enable_qos', False, False, lambda n, o: n != o, False],
        ['syslog_level', 'error', 'error', lambda n, o: n != o, False],
    ]

    system_configs_build = [
        # [配置名, 新值, 旧值, 替换条件: lambda n, o: n != o, 是否租户级, 重启生效]
        ['memory_chunk_cache_size', '0', '0', lambda n, o: n != o, False, False],
        ['trx_try_wait_lock_timeout', '0ms', '0ms', lambda n, o: n != o, False, False],
        ['large_query_threshold', '1s', '1s', lambda n, o: n != o, False, False],
        ['trace_log_slow_query_watermark', '500ms', '500ms', lambda n, o: n != o, False, False],
        ['syslog_io_bandwidth_limit', '30m', '30m', lambda n, o: n != o, False, False],
        ['enable_async_syslog', 'true', 'true', lambda n, o: n != o, False, False],
        ['merger_warm_up_duration_time', 0, 0, lambda n, o: n != o, False, False],
        ['merger_switch_leader_duration_time', 0, 0, lambda n, o: n != o, False, False],
        ['large_query_worker_percentage', 10, 10, lambda n, o: n != o, False, False],
        ['builtin_db_data_verify_cycle', 0, 0, lambda n, o: n != o, False, False],
        ['enable_merge_by_turn', False, False, lambda n, o: n != o, False, False],
        ['minor_merge_concurrency', 30, 30, lambda n, o: n != o, False, False],
        ['memory_limit_percentage', 85, 85, lambda n, o: n != o, False, False],
        ['memstore_limit_percentage', 80, 80, lambda n, o: n != o, False, False],
        ['freeze_trigger_percentage', 60, 60, lambda n, o: n != o, False, False],
        ['enable_syslog_recycle', True, True, lambda n, o: n != o, False, False],
        ['max_syslog_file_count', 100, 100, lambda n, o: n != o, False, False],
        ['minor_freeze_times', 500, 500, lambda n, o: n != o, False, False],
        ['minor_compact_trigger', 0, 0, lambda n, o: n != o, False, False],
        ['max_kept_major_version_number', 1, 1, lambda n, o: n != o, False, False],
        ['sys_bkgd_io_high_percentage', 90, 90, lambda n, o: n != o, False, False],
        ['sys_bkgd_io_low_percentage', 70, 70, lambda n, o: n != o, False, False],
        ['merge_thread_count', 45, 45, lambda n, o: n != o, False, False],
        ['merge_stat_sampling_ratio', 1, 1, lambda n, o: n != o, False, False],
        ['writing_throttling_trigger_percentage', 75, 75, lambda n, o: n != o, True, False],
        ['writing_throttling_maximum_duration', '15m', '15m', lambda n, o: n != o, False, False],
        ['enable_sql_audit', 'false', 'false', lambda n, o: n != o, False, False],
        ['_enable_clog_rpc_aggregation', 'true', 'true', lambda n, o: n != o, False, False],
        ['enable_early_lock_release', 'false', 'false', lambda n, o: n != o, True, False],
        ['enable_auto_leader_switch', 'false', 'false', lambda n, o: n != o, False, False],
        ['clog_transport_compress_all', 'false', 'false', lambda n, o: n != o, False, False],
        ['sleep', 2],
        ['enable_perf_event', False, False, lambda n, o: n != o, False, False],
        ['use_large_pages', 'true', 'true', lambda n, o: n != o, False, True, False],
        ['micro_block_merge_verify_level', 0, 0, lambda n, o: n != o, False, False],
        ['builtin_db_data_verify_cycle', 0, 0, lambda n, o: n != o, False, False],
        ['net_thread_count', 6, 6, lambda n, o: n != o, False, True],
        ['_clog_aggregation_buffer_amount', 4, 4, lambda n, o: n != o, True, False],
        ['_flush_clog_aggregation_buffer_timeout', '2ms', '2ms', lambda n, o: n != o, True, False],
    ]

    odp_configs_test = []

    system_configs_test = [
        # [配置名, 新值, 旧值, 替换条件: lambda n, o: n != o, 是否租户级, 重启生效]
        ['writing_throttling_trigger_percentage', 100, 100, lambda n, o: n != o, True, False],
        ['writing_throttling_maximum_duration', '1h', '1h', lambda n, o: n != o, False, False],
        ['memstore_limit_percentage', 80, 80, lambda n, o: n != o, False, False],
        ['freeze_trigger_percentage', 30, 30, lambda n, o: n != o, False, False],
        ['large_query_threshold', '200s', '200s', lambda n, o: n != o, False, False],
        ['trx_try_wait_lock_timeout', '0ms', '0ms', lambda n, o: n != o, False, False],
        ['cpu_quota_concurrency', 4, 4, lambda n, o: n != o, False, False],
        ['minor_warm_up_duration_time', 0, 0, lambda n, o: n != o, False, False],
        ['minor_freeze_times', 500, 500, lambda n, o: n != o, False, False],
        ['minor_compact_trigger', 3, 3, lambda n, o: n != o, False, False],
        ['sys_bkgd_io_high_percentage', 90, 90, lambda n, o: n != o, False, False],
        ['sys_bkgd_io_low_percentage', 70, 70, lambda n, o: n != o, False, False],
        ['minor_merge_concurrency', 20, 20, lambda n, o: n != o, False, False],
        ['builtin_db_data_verify_cycle', 0, 0, lambda n, o: n != o, False, False],
        ['trace_log_slow_query_watermark', '10s', '10s', lambda n, o: n != o, False, False],
        ['gts_refresh_interval', '500us', '500us', lambda n, o: n != o, False, False],
        ['server_permanent_offline_time', '36000s', '36000s', lambda n, o: n != o, False, False],
        ['weak_read_version_refresh_interval', 0, 0, lambda n, o: n != o, False, False],
        ['_ob_get_gts_ahead_interval', '1ms', '1ms', lambda n, o: n != o, False, False],
        ['bf_cache_priority', 10, 10, lambda n, o: n != o, False, False],
        ['user_block_cache_priority', 5, 5, lambda n, o: n != o, False, False],
        ['merge_stat_sampling_ratio', 1, 1, lambda n, o: n != o, False, False],
        ['enable_sql_audit', 'false', 'false', lambda n, o: n != o, False, False],
        ['bf_cache_miss_count_threshold', 1, 1, lambda n, o: n != o, False, False],
        ['__easy_memory_limit', '20G', '20G', lambda n, o: n != o, False, False],
        ['_enable_defensive_check', 'false', 'false', lambda n, o: n != o, False, False],
        ['binlog_row_image', 'MINIMAL', 'MINIMAL', lambda n, o: n != o, False, False],
        ['sleep', 2],
        ['syslog_level', 'PERF', 'PERF', lambda n, o: n != o, False, False],
        ['max_syslog_file_count', 100, 100, lambda n, o: n != o, False, False],
        ['enable_syslog_recycle', True, True, lambda n, o: n != o, False, False],
        ['ob_enable_batched_multi_statement', True, True, lambda n, o: n != o, True, False],
        ['_cache_wash_interval', '1m', '1m', lambda n, o: n != o, False, False],
        ['cache_wash_threshold', '10G', '10G', lambda n, o: n != o, False, False],
        ['plan_cache_evict_interval', '30s', '30s', lambda n, o: n != o, False, False],
        ['enable_one_phase_commit', 'false', 'false', lambda n, o: n != o, False, False],
        ['use_large_pages', 'true', 'true', lambda n, o: n != o, False, False],
        ['enable_monotonic_weak_read', 'false', 'false', lambda n, o: n != o, False, False],
    ]

    odp_configs = odp_configs_build if optimization_step == 'build' else odp_configs_test
    system_configs = system_configs_build if optimization_step == 'build' else system_configs_test

    try:
        if odp_cursor and optimization:
            for config in odp_configs:
                if not config[4] or optimization > 1:
                    sql = 'show proxyconfig like "%s"' % config[0]
                    ret = execute(odp_cursor, sql)
                    if ret:
                        if config[0] in ['syslog_level']:
                            config[2] = ret['level']
                        else:
                            config[2] = ret['value']
                        if config[3](*type_transform(config[1], config[2])):
                            sql = 'alter proxyconfig set %s=%%s' % config[0]
                            if config[4]:
                                odp_need_reboot = True
                            execute(odp_cursor, sql, [config[1]])
                            odp_configs_done.append(config)
                    else:
                        stdio.verbose("proxy config %s not found, skip" % config[0])

        tenant_q = ' tenant="%s"' % tenant_name
        server_num = len(cluster_config.servers)

        if optimization and ob_optimization:
            for config in system_configs:
                if config[0] == 'sleep':
                    sleep(config[1])
                    system_configs_done.append(config)
                    continue
                if not config[5] or optimization > 1:
                    sql = 'select value from oceanbase.__all_virtual_sys_parameter_stat where name="%s"' % config[0]
                    if config[4]:
                        sql = 'select * from oceanbase.__all_virtual_tenant_parameter_info ' \
                              'where name like "%s" and tenant_id=%d' % (config[0], tenant_meta['tenant_id'])
                    ret = execute(cursor, sql)
                    if ret:
                        config[2] = ret['value']
                        if config[3](*type_transform(config[1], config[2])):
                            sql = 'alter system set %s=%%s' % config[0]
                            if config[4]:
                                sql += tenant_q
                            if config[5]:
                                obs_need_reboot = True
                            execute(cursor, sql, [config[1]])
                            system_configs_done.append(config)
                    else:
                        stdio.verbose("system parameter %s not found, skip" % config[0])

            sql = "select count(1) server_num from oceanbase.__all_server where status = 'active'"
            ret = execute(cursor, sql)
            if ret:
                server_num = ret.get("server_num", server_num)

            max_cpu = kwargs.get('cpu_total')
            parallel_servers_target = int(max_cpu * server_num * 8)

            tenant_variables_build = [
                # [变量名, 新值, 旧值, 替换条件: lambda n, o: n != o]
                ['ob_plan_cache_percentage', 20, 20, lambda n, o: n != o],
                ['autocommit', 1, 1, lambda n, o: n != o],
                ['ob_query_timeout', 36000000000, 36000000000, lambda n, o: n != o],
                ['ob_trx_timeout', 36000000000, 36000000000, lambda n, o: n != o],
                ['max_allowed_packet', 67108864, 67108864, lambda n, o: n != o],
                ['ob_sql_work_area_percentage', 100, 100, lambda n, o: n != o],
                ['parallel_servers_target', parallel_servers_target, parallel_servers_target, lambda n, o: n != o],
            ]
            tenant_variables_test = []
            tenant_variables = tenant_variables_build if optimization_step == 'build' else tenant_variables_test

            select_sql_t = "select value from oceanbase.__all_virtual_sys_variable where tenant_id = %d and name = '%%s'" % \
                           tenant_meta['tenant_id']
            update_sql_t = "ALTER TENANT %s SET VARIABLES %%s = %%%%s" % tenant_name

            for config in tenant_variables:
                sql = select_sql_t % config[0]
                ret = execute(cursor, sql)
                if ret:
                    value = ret['value']
                    config[2] = int(value) if isinstance(value, str) and value.isdigit() else value
                    if config[3](*type_transform(config[1], config[2])):
                        sql = update_sql_t % config[0]
                        tenant_variables_done.append(config)
                        execute(cursor, sql, [config[1]])
                else:
                    stdio.verbose("tenant config %s not found, skip" % config[0])
            if len(odp_configs_done) + len(system_configs_done) + len(tenant_variables_done) - variables_count_before:
                sleep(3)

        success = True

    except KeyboardInterrupt as e:
        stdio.exception(e)
    except Exception:
        stdio.exception('')
    finally:
        if success:
            stdio.stop_loading('succeed')
            plugin_context.return_true(
                odp_configs_done=odp_configs_done,
                system_configs_done=system_configs_done,
                tenant_variables_done=tenant_variables_done,
                tenant_id=tenant_meta['tenant_id'],
                odp_need_reboot=odp_need_reboot,
                obs_need_reboot=obs_need_reboot
            )
        else:
            stdio.stop_loading('fail')
            plugin_context.return_false(
                odp_configs_done=odp_configs_done,
                system_configs_done=system_configs_done,
                tenant_variables_done=tenant_variables_done,
                tenant_id=tenant_meta['tenant_id'],
                odp_need_reboot=odp_need_reboot,
                obs_need_reboot=obs_need_reboot
            )