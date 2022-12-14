call dbms_stats.gather_table_stats('test', 'lineitem', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'orders', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'partsupp', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'part', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'customer', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'supplier', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'nation', degree=>{cpu_total},  granularity=>'AUTO', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('test', 'region', degree=>{cpu_total},  granularity=>'AUTO', method_opt=>'FOR ALL COLUMNS SIZE AUTO');