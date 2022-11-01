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
    l_orderkey BIGINT NOT NULL,
    l_partkey BIGINT NOT NULL,
    l_suppkey INTEGER NOT NULL,
    l_linenumber INTEGER NOT NULL,
    l_quantity DECIMAL(15,2) NOT NULL,
    l_extendedprice DECIMAL(15,2) NOT NULL,
    l_discount DECIMAL(15,2) NOT NULL,
    l_tax DECIMAL(15,2) NOT NULL,
    l_returnflag char(1) DEFAULT NULL,
    l_linestatus char(1) DEFAULT NULL,
    l_shipdate date NOT NULL,
    l_commitdate date DEFAULT NULL,
    l_receiptdate date DEFAULT NULL,
    l_shipinstruct char(25) DEFAULT NULL,
    l_shipmode char(10) DEFAULT NULL,
    l_comment varchar(44) DEFAULT NULL,
    primary key(l_orderkey, l_linenumber))row_format = condensed
    tablegroup = tpch_tg_lineitem_order_group
    partition by key (l_orderkey) partitions cpu_num;

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
    primary key (o_orderkey))row_format = condensed
    tablegroup = tpch_tg_lineitem_order_group
    partition by key(o_orderkey) partitions cpu_num;

drop table if exists partsupp;
    create table partsupp (
    ps_partkey bigint not null,
    ps_suppkey bigint not null,
    ps_availqty bigint default null,
    ps_supplycost bigint default null,
    ps_comment varchar(199) default null,
    primary key (ps_partkey, ps_suppkey))row_format = condensed
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
  primary key (p_partkey))row_format = condensed
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
  primary key (c_custkey))row_format = condensed
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
  primary key (s_suppkey))row_format = condensed
  partition by key(s_suppkey) partitions cpu_num;


drop table if exists nation;
    create table nation (
  n_nationkey bigint not null,
  n_name char(25) default null,
  n_regionkey bigint default null,
  n_comment varchar(152) default null,
  primary key (n_nationkey))row_format = condensed;

drop table if exists region;
    create table region (
  r_regionkey bigint not null,
  r_name char(25) default null,
  r_comment varchar(152) default null,
  primary key (r_regionkey))row_format = condensed;