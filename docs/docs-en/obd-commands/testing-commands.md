# Testing commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

## `obd test mysqltest`

Runs the mysqltest on the specified node of an OcecanBase cluster or ODP. To run the mysqltest, you must install OBClient.

```shell
obd test mysqltest <deploy name> [--test-set <test-set>] [flags]
```

`deploy name` specifies the name of the deployment configuration file.

This table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -c/--component | No | string |   | The name of the component to be tested. Valid values: `oceanbase-ce`, `oceanbase`, `obproxy-ce` and `obproxy`. If you do not specify a value, the existence of `obproxy`, `obproxy-ce`, `oceanbase`, `oceanbase-ce` is checked sequentially. The traversal stops when a component is found, and the component is then tested.   |
| --test-server | No | string | The first node of the specified component.  | It must be the name of a node of the specified component.  |
| --user | No | string | root | The username for running the test.  |
| --password | No | string |   | The password for running the test.  |
| --mysqltest-bin | No | string | mysqltest | The path of the mysqltest binary file.  |
| --obclient-bin | No | string | obclient | The path of the OBClient binary file.  |
| --test-dir | No | string | ./mysql_test/t | The directory that stores the test file required for the mysqltest. If no test file is found in the directory, OBD will search for a built-in test file.  |
| --result-dir | No | string | ./mysql_test/r | The directory that stores the result file required for the mysqltest. If no result file is found in the directory, OBD will search for a built-in result file.  |
| --tmp-dir | No | string | ./tmp | The mysqltest tmpdir option.  |
| --var-dir | No | string | ./var | The directory to create the log directory. The log directory will be added to the mysqltest command as the logdir option.  |
| --test-set | No | string | None | The test case array. Separate multiple test cases with commas (,).  |
| --test-pattern | No | string | None | The regular expression for matching test file names. Test cases matching the regular expression will overwrite the values of the test-set option.  |
| --suite | No | string | None | The suite array. A suite contains multiple tests. Separate multiple tests with commas (,). If this option is enabled, the --test-pattern and --test-set options will become invalid.  |
| --suite-dir | No | string | ./mysql_test/test_suite | The directory that stores the suite directory. If no suite directory is found in the directory, OBD will search for a built-in suite directory.  |
| --all | No | bool | false | Specifies whether to run all test cases in the directory specified for the --suite-dir option. The --suite-dir option specifies the directory that stores the suite directory.  |
| --need-init | No | bool | false | Specifies whether to run the init sql files. Before OBD runs the mysqltest on a new cluster, it may run some initialization files. For example, it may create some accounts or tenants required for running the test cases. The --suite-dir option specifies the directory that stores the suite directory. This option is disabled by default.  |
| --init-sql-dir | No | string | ../ | The directory that stores the init sql files. If no init sql file is found in the directory, OBD will search for built-in init sql files.  |
| --init-sql-files | No | string | | The init sql files to be run when initialization is required. Separate multiple init sql files with commas (,). If this option is not specified but initialization is required, OBD will run the built-in init files based on the cluster configurations.  |
| --auto-retry | No | bool | false | Specifies whether to automatically redeploy the cluster for a retry after a test fails.  |

## `obd test sysbench`

Runs the Sysbench test on the specified node of an OcecanBase cluster or ODP.  To run the Sysbench test, you must install OBClient and ob-sysbench.

```shell
obd test sysbench <deploy name> [flags]
```

`deploy name` specifies the name of the deployment configuration file.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -c/--component | No | string |   | The name of the component to be tested. Valid values: `oceanbase-ce`, `oceanbase`, `obproxy-ce` and `obproxy`. If you do not specify a value, the existence of `obproxy`, `obproxy-ce`, `oceanbase`, `oceanbase-ce` is checked sequentially. The traversal stops when a component is found, and the component is then tested.   |
| --test-server | No | string | The first node of the specified component.  | It must be the name of a node of the specified component.  |
| --user | No | string | root | The username for running the test.  |
| --password | No | string |   | The password for running the test.  |
| --tenant | No | string | test | The tenant name for running the test.  |
| --database | No | string | test | The database for performing the test.  |
| --obclient-bin | No | string | obclient | The path of the OBClient binary file.  |
| --sysbench-bin | No | string | sysbench | The path of the Sysbench binary file.  |
| --script-name | No | string | point_select.lua | The name of the Sysbench script to be run.  |
| --sysbench-script-dir | No | string | /usr/sysbench/share/sysbench | The directory that stores the Sysbench script.  |
| --tables | No | int | 30 | The number of tables to be initialized.  |
| --table-size | No | int | 20000 | The data size of each table to be initialized.  |
| --threads | No | int | 16 | The number of threads to be started.  |
| --time | No | int | 60 | The running duration. When this option is set to 0, the running duration is not limited.  |
| --interval | No | int | 10 | The logging interval, in seconds.  |
| --events | No | int | 0 | The maximum number of requests. If this option is specified, the --time option is not needed.  |
| --rand-type | No | string |   | The random number generation function used for data access. Valid values: special, uniform, gaussian, and pareto.  Default value: special, early value: uniform.  |
| ---skip-trx | No | string |   | Specifies whether to enable or disable a transaction in a read-only test.  |
| -O/--optimization | No | int | 1 | Auto tuning level. Off when 0.  |

## `obd test tpch`

This section describes how to run the TPC-H test on the specified node of an OcecanBase cluster or ODP. To run the TPC-H test, you must install OBClient and obtpch.
TPC-H needs to specify an OceanBase target server as the execution target. Before executing the TPC-H test, OBD will transfer the data files required for the test to the specified directory of the specified machine. Please make sure that you have enough disk space on this machine because these files may be relatively large.
Of course, you can prepare the data files on the target machine in advance and then turn off the transfer by using the `-dt/--disable-transfer` option.

```shell
obd test tpch <deploy name> [flags]
```

`deploy name` specifies the name of the deployment configuration file.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| --test-server | No | string | The first node of the specified component.  | It must be the name of a node of the specified component.  |
| --user | No | string | root | The username for running the test.  |
| --password | No | string |   | The password for running the test.  |
| --tenant | No | string | test | The tenant name for running the test.  |
| --database | No | string | test | The database for performing the test.  |
| --obclient-bin | No | string | obclient | The path of the OBClient binary file.  |
| --dbgen-bin | No | string | /usr/local/tpc-h-tools/bin/dbgen | The path of the dbgen binary file.  |
| --dss-config | No | string | /usr/local/tpc-h-tools/ | The directory that stores the dists.dss files.  |
| -s/--scale-factor | No | int | 1 | Automatically generate the scale of test data, the data is measured in Gigabytes.  |
| --tmp-dir | No | string | ./tmp | Temporary directory when executing tpch. When enabled, this option will automatically generate test data, auto-tuned SQL files, log files for executing test SQL, and so on.  |
| --ddl-path | No | string |   | The path or directory of the ddl file. If it is empty, OBD will use the ddl file that comes with it.  |
| --tbl-path | No | string |   | The path or directory of the tbl file. If it is empty, use dbgen to generate test data.  |
| --sql-path | No | string |   | The path or directory of the sql file. If it is empty, OBD will use the sql file that comes with it.  |
| --remote-tbl-dir | No | string |   | The directory where the tbl is stored on the target observer, it is the absolute path. Please make sure that you have the read and write permissions to this directory when you start the server. This option is required when  `--test-only` is not enabled.  |
| --test-only | No | bool | false | When you enable this option, initialization will not be done, only the test SQL is exectued.  |
| --dt/--disable-transfer | No | bool | false | Disable transfer. When you enable this option, OBD will not transfer the local tbl to the remote remote-tbl-dir, and OBD will directly use the tbl file under the target machine remote-tbl-dir.  |
| -O/--optimization | No | int | 1 | Auto tuning level. Off when 0.  |

## obd test tpcc

You can run this command to perform a TPC-C test on a specified node of an OceanBase cluster or an OceanBase Database Proxy (ODP) component.

Make sure that you have installed OBClient and obtpcc, which are required to perform a TPC-C test.

```shell
obd test tpcc <deploy name> [flags]
```

The `deploy name` parameter specifies the name of the deployed cluster. You can consider it as an alias for the configuration file.

The following table describes details about the available options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| --component | No | string | Empty  | The name of the component to be tested. Valid values: `oceanbase-ce`, `oceanbase`, `obproxy-ce` and `obproxy`. If you do not specify a value, the existence of `obproxy`, `obproxy-ce`, `oceanbase`, `oceanbase-ce` is checked sequentially. The traversal stops when a component is found, and the component is then tested.  |
| --test-server | No | string | The name of the first node under the specified component.  | The name of the node to be tested under the specified component.  |
| --user | No | string | root  | The username used to perform the test.  |
| --password | No | string | Empty  | The user password used to perform the test.  |
| --tenant | No | string | test  | The tenant name used to perform the test.  |
| --database | No | string | test  | The database where the test is to be performed.  |
| --obclient-bin | No | string | obclient  | The path to the directory where the binary files of OBClient are stored. |
| --java-bin | No | string | java  | The path to the directory where the Java binary files are stored.  |
| --tmp-dir | No | string | ./tmp  | The temporary directory to be used for the TPC-C test. Automatically generated configuration files, auto-tuned SQL files, and test output files will be stored in this directory.  |
| --bmsql-dir | No | string | Empty  | The installation directory of BenchmarkSQL. You need to specify this option only if you manually compile and install BenchmarkSQL. If you use obtpcc, this option is not required.  |
| --bmsql-jar | No | string | Empty  | The path to the directory where the JAR file of BenchmarkSQL is stored. If you do not specify the path, and the BenchmarkSQL directory is not specified, the default installation directory generated by obtpcc is used. If the BenchmarkSQL directory is specified, the JAR file in the `<bmsql-dir>/dist` directory is used.  |
| --bmsql-libs | No | string | Empty  | If the BenchmarkSQL directory is specified, the JAR files in the `<bmsql-dir>/lib` and `<bmsql-dir>/lib/oceanbase` directories are used. If you use obtpcc, this option is not required.  |
| --bmsql-sql-dir | No | string | Empty  | The path to the directory where the SQL files for the TPC-C test are stored. If you do not specify the path, OceanBase Deployer (OBD) uses the SQL files that are automatically generated.  |
| --warehouses | No | int | Empty  | The number of warehouses for the TPC-C test data set. If you do not specify a value, the assigned value is 20 times the number of CPU cores allocated to the OceanBase cluster.  |
| --load-workers | No | int | Empty  | The number of concurrent worker threads for building the test data set. If you do not specify a value, the number of CPU cores per server or the size of tenant memory (GB)/2, whichever is smaller, is used.  |
| --terminals | No | int | Empty  | The number of virtual terminals to be used for the TPC-C test. If you do not specify a value, the number of CPU cores for the OceanBase cluster ?? 15 or the number of warehouses ?? 10, whichever is smaller, is used.  |
| --run-mins | No | int | 10  | The amount of time allocated for the execution of the TPC-C test.  |
| --test-only | No | bool | false  | Specifies that the test is performed without data construction.  |
| -O/--optimization | No | int | 1  | The degree of auto-tuning. Valid values: `0`, `1`, and `2`. `0` indicates that auto-tuning is disabled. `1` indicates that the auto-tuning parameters that take effect without a cluster restart are modified. `2` indicates that all auto-tuning parameters are modified. If necessary, the cluster is restarted to make all parameters take effect.  |