system sleep 5;
alter system set  balancer_idle_time = '60s';
create user 'admin' IDENTIFIED BY 'admin';
use oceanbase;
create database if not exists test;

use test;
grant all on *.* to 'admin' WITH GRANT OPTION;


set global ob_enable_jit='OFF';
alter system set large_query_threshold='1s';
alter system set syslog_level='info';
alter system set syslog_io_bandwidth_limit='30M';
alter system set trx_try_wait_lock_timeout='0';
alter system set zone_merge_concurrency=0;
alter system set merger_completion_percentage=100;
alter system  set trace_log_slow_query_watermark='500ms';
alter system set minor_freeze_times=30;
alter system set clog_sync_time_warn_threshold = '1000ms';
alter system set trace_log_slow_query_watermark = '10s';
alter system set enable_sql_operator_dump = 'false';
alter system set rpc_timeout=1000000000;


create resource unit tpch_box1 min_memory '100g', max_memory '100g', max_disk_size '1000g', max_session_num 64, min_cpu=9, max_cpu=9, max_iops 128, min_iops=128;
create resource pool tpch_pool1 unit = 'tpch_box1', unit_num = 1, zone_list = ('z1', 'z2', 'z3');
create tenant oracle replica_num = 3, resource_pool_list=('tpch_pool1') set ob_tcp_invited_nodes='%', ob_compatibility_mode='oracle';

alter tenant oracle set variables autocommit='on';
alter tenant oracle set variables nls_date_format='yyyy-mm-dd hh24:mi:ss';
alter tenant oracle set variables nls_timestamp_format='yyyy-mm-dd hh24:mi:ss.ff';
alter tenant oracle set variables nls_timestamp_tz_format='yyyy-mm-dd hh24:mi:ss.ff tzr tzd';
alter tenant oracle set variables ob_query_timeout=7200000000;
alter tenant oracle set variables ob_trx_timeout=7200000000;
alter tenant oracle set variables max_allowed_packet=67108864;
alter tenant oracle set variables ob_enable_jit='OFF';
alter tenant oracle set variables ob_sql_work_area_percentage=80;
alter tenant oracle set variables parallel_max_servers=512;
alter tenant oracle set variables parallel_servers_target=512;

select count(*) from oceanbase.__all_server group by zone limit 1 into @num;
set @sql_text = concat('alter resource pool tpch_pool1', ' unit_num = ', @num);
prepare stmt from @sql_text;
execute stmt;
deallocate prepare stmt;
