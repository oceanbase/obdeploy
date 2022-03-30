create index bmsql_customer_idx1 on  bmsql_customer (c_w_id, c_d_id, c_last, c_first) local;
create index bmsql_oorder_idx1 on  bmsql_oorder (o_w_id, o_d_id, o_carrier_id, o_id) local;