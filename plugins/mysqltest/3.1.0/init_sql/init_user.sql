use oceanbase;
create user 'admin' IDENTIFIED BY 'admin';
grant all on *.* to 'admin' WITH GRANT OPTION;
create database obproxy;

alter system set _enable_split_partition = true;
