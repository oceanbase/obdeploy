# 测试命令组

OBD 有多级命令，您可以在每个层级中使用 `-h/--help` 选项查看子命令的帮助信息。本文将介绍 OBD 中测试命令的使用。

## obd test mysqltest

使用该命令可对 OcecanBase 数据库或 ODP 组件的指定节点执行 mysqltest。

执行 mysqltest 需要 OBClient，请先确认您已安装 OBClient。

```shell
obd test mysqltest <deploy name> [--test-set <test-set>] [flags]
```

参数 `deploy name` 为部署集群名，可以理解为配置文件的别名。

选项说明见下表：

|       选项名        | 是否必选 |  数据类型  |           默认值           |                                                     说明                                                     |
|------------------|------|--------|-------------------------|------------------------------------------------------------------------------------------------------------|
| -c/--component   | 否    | string | 默认为空                    | 待测试的组件名。候选项为 `obproxy`、`obproxy-ce`、`oceanbase` 和 `oceanbase-ce`。为空时，按 `obproxy`、`obproxy-ce`、`oceanbase`、`oceanbase-ce` 的顺序进行检查。检查到组件存在则不再遍历，使用命中的组件进行后续测试。 |
| --test-server    | 否    | string | 默指定的组件下服务器中的第一个节点       | 必须是指定的组件下的某个节点名。                                                                                           |
| --user           | 否    | string | root                    | 执行测试的用户名。                                                                                                  |
| --password       | 否    | string | 默认为空                    | 执行测试的用户密码。                                                                                                 |
| --mysqltest-bin  | 否    | string | mysqltest               | mysqltest 二进制文件路径。                                                                                         |
| --obclient-bin   | 否    | string | obclient                | OBClient 二进制文件路径。                                                                                          |
| --test-dir       | 否    | string | ./mysql_test/t          | mysqltest 所需的 `test-file` 存放的目录。test 文件找不到时会尝试在 OBD 内置中查找。                                                 |
| --result-dir     | 否    | string | ./mysql_test/r          | mysqltest 所需的 `result-file` 存放的目录。result 文件找不到时会尝试在 OBD 内置中查找。                                             |
| --tmp-dir        | 否    | string | ./tmp                   | 为 mysqltest tmpdir 选项。                                                                                     |
| --var-dir        | 否    | string | ./var                   | 将在该目录下创建 log 目录并作为 logdir 选项传入 mysqltest。                                                                  |
| --test-set       | 否    | string | 无                       | test case 数组。多个数组使用英文逗号 `,` 间隔。                                                                            |
| --test-pattern   | 否    | string | 无                       | test 文件名匹配的正则表达式。所有匹配表达式的 case 将覆盖 `test-set` 选项。                                                          |
| --suite          | 否    | string | 无                       | suite 数组。一个 suite 下包含多个 test。可以使用英文逗号 `,` 间隔。使用该选项后 `--test-pattern` 和 `--test-set` 都将失效。                  |
| --suite-dir      | 否    | string | ./mysql_test/test_suite | 存放 suite 目录的目录。suite 目录找不到时会尝试在 OBD 内置中查找。                                                                 |
| --all            | 否    | bool   | false                   | 执行 `--suite-dir` 下全部的 case。存放 suite 目录的目录。                                                                 |
| --need-init      | 否    | bool   | false                   | 执行 init sql 文件。一个新的集群要执行 mysqltest 前可能需要执行一些初始化文件，比如创建 case 所需要的账号和租户等。存放 suite 目录的目录。默认不开启。               |
| --init-sql-dir   | 否    | string | ../                      | init sql 文件所在目录。sql 文件找不到时会尝试在 OBD 内置中查找。                                                                  |
| --init-sql-files | 否    | string |                         | 需要 init 时执行的 init sql 文件数组。英文逗号 `,` 间隔。不填时，如果需要 init，OBD 会根据集群配置执行内置的 init。                                |
| --auto-retry     | 否    | bool   | false                   | 失败时自动重部署集群进行重试。                                                                                            |

## obd test sysbench

使用该命令可对 OcecanBase 数据库或 ODP 组件的指定节点执行 Sysbench。

执行 Sysbench 需要 OBClient 和 ob-sysbench，请确认您已安装 OBClient 和 ob-sysbench。

```shell
obd test sysbench <deploy name> [flags]
```

参数 `deploy name` 为部署集群名，可以理解为配置文件的别名。

选项说明见下表：

|          选项名          | 是否必选 |  数据类型  |             默认值              |                                                     说明                                                     |
|-----------------------|------|--------|------------------------------|------------------------------------------------------------------------------------------------------------|
| -c/--component           | 否    | string | 默认为空                      | 待测试的组件名。候选项为 `obproxy`、`obproxy-ce`、`oceanbase` 和 `oceanbase-ce`。为空时，按 `obproxy`、`obproxy-ce`、`oceanbase`、`oceanbase-ce` 的顺序进行检查。检查到组件存在则不再遍历，使用命中的组件进行后续测试。 |
| --test-server         | 否    | string | 默认为指定的组件下服务器中的第一个节点 | 必须是指定的组件下的某个节点名。                                                                                           |
| --user                | 否    | string | root                         | 执行测试的用户名。                                                                                                  |
| --password            | 否    | string | 默认为空                      | 执行测试的用户密码。                                                                                                 |
| --tenant              | 否    | string | test                         | 执行测试的租户名。                                                                                                  |
| --database            | 否    | string | test                         | 执行测试的数据库。                                                                                                  |
| --obclient-bin        | 否    | string | obclient                     | OBClient 二进制文件路径。                                                                                          |
| --sysbench-bin        | 否    | string | sysbench                     | sysbench 二进制文件路径。                                                                                          |
| --script-name         | 否    | string | point_select.lua             | 要执行的 sysbench 脚本名。                                                                                         |
| --sysbench-script-dir | 否    | string | /usr/sysbench/share/sysbench | sysbench 脚本存放目录。                                                                                           |
| --tables              | 否    | int    | 30                           | 初始化表的数量。                                                                                                   |
| --table-size          | 否    | int    | 20000                        | 每张表初始化的数据数量。                                                                                               |
| --threads             | 否    | int    | 16                           | 启动的线程数量。                                                                                                   |
| --time                | 否    | int    | 60                           | 运行时间。设置为 `0` 时表示不限制时间。                                                                                     |
| --interval            | 否    | int    | 10                           | 运行期间日志，单位：为秒。                                                                                              |
| --events              | 否    | int    | 0                            | 最大请求数量，定义数量后可以不需要 `--time` 选项。                                                                             |
| --rand-type           | 否    | string | 空                            | 访问数据时使用的随机生成函数。取值可以为 special、uniform、gaussian 或 pareto。默认值为 `special`， 早期值为 `uniform`。                    |
| ---skip-trx           | 否    | string | 空                            | 在只读测试中打开或关闭事务。                                                                                             |
| -O/--optimization     | 否    | int    | 1                            | 自动调优等级。为 `0` 时关闭。                                                                                          |

## obd test tpch

使用该命令可对 OcecanBase 数据库或 ODP 组件的指定节点执行 TPC-H。

执行 TPC-H 需要 OBClient 和 obtpch，请确认您已安装 OBClient 和 obtpch。

TPC-H 需要指定一台 OceanBase 目标服务器作为执行对象。在执行 TPC-H 测试前，OBD 会将测试需要的数据文件传输到指定机器的指定目录下，这些文件可能会比较大，请确保机器上足够的磁盘空间。当然您也可以提前在目标机器上准备好数据文件，再通过 `--dt/--disable-transfer` 选项关闭传输。

```shell
obd test tpch <deploy name> [flags]
```

参数 `deploy name` 为部署集群名，可以理解为配置文件的别名。

选项说明见下表：

|           选项名           | 是否必选 |  数据类型  |               默认值                |                                            说明                                            |
|-------------------------|------|--------|----------------------------------|------------------------------------------------------------------------------------------|
| --test-server           | 否    | string | 默认为指定的组件下服务器中的第一个节点                | 必须是指定的组件下的某个节点名。                                                                         |
| --user                  | 否    | string | root                             | 执行测试的用户名。                                                                                |
| --password              | 否    | string | 默认为空                             | 执行测试的用户密码。                                                                               |
| --tenant                | 否    | string | test                             | 执行测试的租户名，请确保该租户已经创建。                                                                                |
| --database              | 否    | string | test                             | 执行测试的数据库，如没有创建，测试程序会自动创建。                                                                                |
| --obclient-bin          | 否    | string | obclient                         | OBClient 二进制文件路径。                                                                        |
| --dbgen-bin             | 否    | string | /usr/local/tpc-h-tools/bin/dbgen | dbgen 二进制文件路径。                                                                           |
| --dss-config            | 否    | string | /usr/local/tpc-h-tools/          | `dists.dss` 所在目录。                                                                        |
| -s/--scale-factor       | 否    | int    | 1                                | 自动生成测试数据的规模，单位：G。                                                                        |
| --tmp-dir                | 否    | string | ./tmp                            | 执行 tpch 时的临时目录。自动生成的测试数据，自动调优的 sql 文件，执行测试 sql 的日志文件等都会存在这里。                             |
| --ddl-path              | 否    | string | 默认为空                             | ddl 文件路径或目录。为空时，OBD 会使用自带的 ddl 文件。                                                       |
| --tbl-path              | 否    | string | 默认为空                             | tbl 文件路径或目录。为空时，使用 dbgen 生成测试数据。                                                         |
| --sql-path              | 否    | string | 默认为空                             | sql 文件路径或目录。为空时，OBD 会使用自带的 sql 文件。                                                       |
| --remote-tbl-dir        | 否    | string | 默认为空                             | 目标 OBServer 上存放 tbl 的目录，绝对路径，请保证 OBServer 的启动用户对该目录有读写权限。在不开启 `--test-only` 的情况下该选项为必填项。 |
| --test-only             | 否    | bool   | false                            | 不执行初始化，仅执行测试 SQL。                                                                        |
| --dt/--disable-transfer | 否    | bool   | false                            | 禁用传输。开启后将不会把本地 tbl 传输到远程 `remote-tbl-dir` 下，而是直接使用目标机器 `remote-tbl-dir` 下的 `tbl` 文件。     |
| -O/--optimization       | 否    | int    | 1                                | 自动调优等级。为 `0` 时关闭。                                                                        |

## obd test tpcc

使用该命令可对 OceanBase 数据库或 ODP 组件的指定节点执行 TPC-C。

执行 TPC-C 需要 OBClient 和 obtpcc，请确认您已安装 OBClient 和 obtpcc。

```shell
obd test tpcc <deploy name> [flags]
```

参数 `deploy name` 为部署集群名，可以理解为配置文件的别名。

选项说明见下表：

|           选项名           | 是否必选 |  数据类型  |               默认值                |                                            说明                                            |
|-------------------------|------|--------|----------------------------------|------------------------------------------------------------------------------------------|
| --component        | 否    | string |默认为空                             | 待测试的组件名。候选项为 `obproxy`、`obproxy-ce`、`oceanbase` 和 `oceanbase-ce`。为空时，按 `obproxy`、`obproxy-ce`、`oceanbase`、`oceanbase-ce` 的顺序进行检查。检查到组件存在则不再遍历，使用命中的组件进行后续测试。 |
| --test-server        | 否    | string | 默认为指定的组件下服务器中的第一个节点                             | 必须是指定的组件下的某个节点名。 |
| --user        | 否    | string | root                             | 执行测试的用户名。 |
| --password       | 否    | string | 默认为空                             | 执行测试的用户密码。 |
| --tenant       | 否    | string | test                             | 执行测试的租户名。 |
| --database        | 否    | string | test                             | 执行测试的数据库。 |
| --obclient-bin        | 否    | string | obclient                             | OBClient 二进制文件路径。 |
| --java-bin        | 否    | string | java                             | Java 二进制文件路径。 |
| --tmp-dir        | 否    | string | ./tmp                             | 执行 tpcc 时的临时目录。自动生成的配置文件、自动调优的 sql 文件、执行测试输出文件等都会存在这里。 |
| --bmsql-dir        | 否    | string | 默认为空                             | 指定 BenchmarkSQL 的目录。只有在自行编译安装 BenchmarkSQL 时需要指定，obtpcc 不需要指定此项。 |
| --bmsql-jar        | 否    | string | 默认为空                             | 指定 BenchmarkSQL 主 jar 路径。为空的时候，如果未指定 BenchmarkSQL 的目录，则使用 obtpcc 的默认安装路径，如果指定了 BenchmarkSQL 地址，则使用 `<bmsql-dir>/dist` 下的 jar。 |
| --bmsql-libs        | 否    | string | 默认为空                             | 如果指定了 BenchmarkSQL 地址，则使用 `<bmsql-dir>/lib` 以及 `<bmsql-dir>/lib/oceanbase` 下的 jar，obtpcc 不需要指定此项。 |
| --bmsql-sql-dir        | 否    | string | 默认为空                             | TPC-C 的 sql 文件的路径。为空时，OBD 会使用自行生成的 sql 文件。 |
| --warehouses        | 否    | int | 默认为空                             | TPC-C 测试集的货仓数量。如果没有传入，则为 OceanBase 集群 CPU 数 * 20 。 |
| --load-workers       | 否    | int | 默认为空                             | 构造测试数据集时的并发数量。如果没有传入则在 `单机 CPU 数` 与 `租户可用内存（G）/2` 中取小值。 |
| --terminals        | 否    | int | 默认为空                             | TPC-C 测试时的虚拟终端数量。如果没有传入，则在 `OceanBase 集群 CPU 数 * 15` 与 `货仓数量 * 10` 中取小值。 |
| --run-mins        | 否    | int | 10                             | TPC-C 测试执行的时间。 |
| --test-only        | 否    | bool | false                             | 不再构造数据，仅执行测试。 |
| -O/--optimization        | 否    | int | 1                             | 自动调优等级。为 `0` 时关闭。为 `1` 时会修改不需要重启生效的调优参数。为 `2` 时会修改所有的调优参数，如果需要，会重启集群使调优生效。 |