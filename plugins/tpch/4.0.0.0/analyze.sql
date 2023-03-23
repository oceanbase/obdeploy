call dbms_stats.gather_table_stats('{database}', 'lineitem', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'orders', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'partsupp', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'part', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'customer', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'supplier', degree=>{cpu_total}, granularity=>'GLOBAL', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'nation', degree=>{cpu_total},  granularity=>'AUTO', method_opt=>'FOR ALL COLUMNS SIZE AUTO');
call dbms_stats.gather_table_stats('{database}', 'region', degree=>{cpu_total},  granularity=>'AUTO', method_opt=>'FOR ALL COLUMNS SIZE AUTO');