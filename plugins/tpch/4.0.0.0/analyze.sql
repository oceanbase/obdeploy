set _force_parallel_query_dop = {cpu_total};
analyze table lineitem partition(lineitem) compute statistics for all columns size auto;
analyze table orders partition(orders) compute statistics for all columns size auto;
analyze table partsupp partition(partsupp) compute statistics for all columns size auto;
analyze table part partition(part) compute statistics for all columns size auto;
analyze table customer partition(customer) compute statistics for all columns size auto;
analyze table supplier partition(supplier) compute statistics for all columns size auto;
analyze table nation compute statistics for all columns size auto;
analyze table region compute statistics for all columns size auto;