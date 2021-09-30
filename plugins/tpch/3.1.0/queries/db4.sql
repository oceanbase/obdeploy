-- using default substitutions
SELECT  /*+   TPCH_Q4 parallel(cpu_num)  no_unnest */ o_orderpriority, count(*) as order_count
from orders
where o_orderdate >= DATE'1993-07-01' and
      o_orderdate < DATE'1993-07-01' + interval '3' month and
      exists ( SELECT *
               from lineitem
               where l_orderkey = o_orderkey and
                     l_commitdate < l_receiptdate )
 group by o_orderpriority
 order by o_orderpriority;
