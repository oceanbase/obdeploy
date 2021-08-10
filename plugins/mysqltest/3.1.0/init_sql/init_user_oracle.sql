alter session set current_schema = SYS;

create user root IDENTIFIED BY root;
grant all on *.* to root WITH GRANT OPTION;
grant dba to root;

create user test IDENTIFIED BY test;
grant all on *.* to test WITH GRANT OPTION;
grant dba to test;
grant all privileges to test;

create user admin IDENTIFIED BY admin;
grant all on *.* to admin WITH GRANT OPTION;
grant dba to admin;
grant all privileges to admin;

alter user LBACSYS account unlock;
grant all on *.* to LBACSYS WITH GRANT OPTION;
grant dba to LBACSYS;

alter user ORAAUDITOR account unlock;
grant all on *.* to ORAAUDITOR WITH GRANT OPTION;
grant dba to ORAAUDITOR;
alter system set "_enable_split_partition" = 'true';

grant read on directory dd to TEST;
set global secure_file_priv = '';
