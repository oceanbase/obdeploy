create resource unit box1 max_cpu 2, max_memory 1073741824, max_iops 128, max_disk_size '5G', max_session_num 64, MIN_CPU=1, MIN_MEMORY=1073741824, MIN_IOPS=128;
create resource pool pool1 unit = 'box1', unit_num = 1;
create tenant ora_tt replica_num = 1, resource_pool_list=('pool1') set ob_tcp_invited_nodes='%', ob_compatibility_mode='oracle';
alter tenant ora_tt set variables autocommit='on';
alter tenant ora_tt set variables nls_date_format='YYYY-MM-DD HH24:MI:SS';
alter tenant ora_tt set variables nls_timestamp_format='YYYY-MM-DD HH24:MI:SS.FF';
alter tenant ora_tt set variables nls_timestamp_tz_format='YYYY-MM-DD HH24:MI:SS.FF TZR TZD';