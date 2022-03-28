drop table if exists lineitem;
drop table if exists orders;
drop table if exists partsupp;
drop table if exists part;
drop table if exists customer;
drop table if exists supplier;
drop table if exists nation;
drop table if exists region;
drop tablegroup if exists tpch_tg_lineitem_order_group;
drop tablegroup if exists tpch_tg_partsupp_part;

create tablegroup if not exists tpch_tg_lineitem_order_group binding true partition by key 1 partitions cpu_num;
create tablegroup if not exists tpch_tg_partsupp_part binding true partition by key 1 partitions cpu_num;

drop table if exists lineitem;
    create table lineitem (
    l_orderkey bigint not null,
    l_partkey bigint not null,
    l_suppkey bigint not null,
    l_linenumber bigint not null,
    l_quantity bigint not null,
    l_extendedprice bigint not null,
    l_discount bigint not null,
    l_tax bigint not null,
    l_returnflag char(1) default null,
    l_linestatus char(1) default null,
    l_shipdate date not null,
    l_commitdate date default null,
    l_receiptdate date default null,
    l_shipinstruct char(25) default null,
    l_shipmode char(10) default null,
    l_comment varchar(44) default null,
    primary key(l_orderkey, l_linenumber))
    tablegroup = tpch_tg_lineitem_order_group
    partition by key (l_orderkey) partitions cpu_num;
    create index I_L_ORDERKEY on lineitem(l_orderkey) local;
    create index I_L_SHIPDATE on lineitem(l_shipdate) local;

drop table if exists orders;
    create table orders (
    o_orderkey bigint not null,
    o_custkey bigint not null,
    o_orderstatus char(1) default null,
    o_totalprice bigint default null,
    o_orderdate date not null,
    o_orderpriority char(15) default null,
    o_clerk char(15) default null,
    o_shippriority bigint default null,
    o_comment varchar(79) default null,
    primary key (o_orderkey))
    tablegroup = tpch_tg_lineitem_order_group
    partition by key(o_orderkey) partitions cpu_num;
    create index I_O_ORDERDATE on orders(o_orderdate) local;


drop table if exists partsupp;
    create table partsupp (
    ps_partkey bigint not null,
    ps_suppkey bigint not null,
    ps_availqty bigint default null,
    ps_supplycost bigint default null,
    ps_comment varchar(199) default null,
    primary key (ps_partkey, ps_suppkey))
    tablegroup tpch_tg_partsupp_part
    partition by key(ps_partkey) partitions cpu_num;


drop table if exists part;
    create table part (
  p_partkey bigint not null,
  p_name varchar(55) default null,
  p_mfgr char(25) default null,
  p_brand char(10) default null,
  p_type varchar(25) default null,
  p_size bigint default null,
  p_container char(10) default null,
  p_retailprice bigint default null,
  p_comment varchar(23) default null,
  primary key (p_partkey))
  tablegroup tpch_tg_partsupp_part
  partition by key(p_partkey) partitions cpu_num;


drop table if exists customer;
    create table customer (
  c_custkey bigint not null,
  c_name varchar(25) default null,
  c_address varchar(40) default null,
  c_nationkey bigint default null,
  c_phone char(15) default null,
  c_acctbal bigint default null,
  c_mktsegment char(10) default null,
  c_comment varchar(117) default null,
  primary key (c_custkey))
  partition by key(c_custkey) partitions cpu_num;

drop table if exists supplier;
  create table supplier (
  s_suppkey bigint not null,
  s_name char(25) default null,
  s_address varchar(40) default null,
  s_nationkey bigint default null,
  s_phone char(15) default null,
  s_acctbal bigint default null,
  s_comment varchar(101) default null,
  primary key (s_suppkey)
) partition by key(s_suppkey) partitions cpu_num;


drop table if exists nation;
    create table nation (
  n_nationkey bigint not null,
  n_name char(25) default null,
  n_regionkey bigint default null,
  n_comment varchar(152) default null,
  primary key (n_nationkey));

drop table if exists region;
    create table region (
  r_regionkey bigint not null,
  r_name char(25) default null,
  r_comment varchar(152) default null,
  primary key (r_regionkey));
