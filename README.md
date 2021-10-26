# OceanBase Deployer

<!--
#
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.
#
-->

<!-- TODO: some badges here -->

OceanBase Deployer (OBD) is an installation and deployment tool for open-source OceanBase software. It is also a package manager for managing all open-source OceanBase software. This topic describes how to install OBD, how to use OBD, and OBD commands.

## Install OBD

You can install OBD by using these methods:

### Method 1: Install OBD by using RPM packages (only for CentOS 7 or later)

```shell
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://mirrors.aliyun.com/oceanbase/OceanBase.repo
sudo yum install -y ob-deploy
source /etc/profile.d/obd.sh
```

### Method 2: Install OBD by using the source code

Before you install OBD by using the source code, make sure that you have installed these dependencies:

- gcc
- wget
- python-devel
- openssl-devel
- xz-devel
- mysql-devel

To install OBD on Python2, run these commands:

```shell
pip install -r requirements.txt
sh build.sh
source /etc/profile.d/obd.sh
```

To install OBD on Python3, run these commands:

```shell
pip install -r requirements3.txt
sh build.sh
source /etc/profile.d/obd.sh
```

## Start an OceanBase cluster

After you install OBD, you can run these commands as the root user to start a local single-node OceanBase cluster.
Before you run the commands, make sure that these conditions are met:

- You have logged on as the root user.
- Ports `2882` and `2883` are available.
- Your server has at least 8 GB of memory.
- Your server has at least 2 CPU cores.

> **NOTE:** If the preceding conditions are not met, see [Use OBD to start an OceanBase cluster](#Use-OBD-to-start-an-OceanBase-cluster).
> **NOTE:** For the convenience of using root here, OBD and OceanBase database do not have any restrictions on running users. We do not recommend that you use root in production.
```shell
obd cluster deploy c1 -c ./example/mini-local-example.yaml
obd cluster start c1
# Connect to the OceanBase Database by using a MySQL client.
mysql -h127.1 -uroot -P2883
```

## Use OBD to start an OceanBase cluster

To start an OceanBase cluster, follow these steps:

### Step 1: Select a configuration file

Select a configuration file based on your resource configurations:

#### Small-scale deployment mode

This deployment mode applies to personal devices with at least 8 GB of memory.

- [Sample configuration file for local single-node deployment](./example/mini-local-example.yaml)
- [Sample configuration file for single-node deployment](./example/mini-single-example.yaml)
- [Sample configuration file for three-node deployment](./example/mini-distributed-example.yaml)
- [Sample configuration file for single-node deployment with ODP](./example/mini-single-with-obproxy-example.yaml)
- [Sample configuration file for three-node deployment with ODP](./example/mini-distributed-with-obproxy-example.yaml)

#### Professional deployment mode

This deployment mode applies to advanced Elastic Compute Service (ECS) instances or physical servers with at least 16 CPU cores and 64 GB of memory.

- [Sample configuration file for local single-node deployment](./example/local-example.yaml)
- [Sample configuration file for single-node deployment](./example/single-example.yaml)
- [Sample configuration file for three-node deployment](./example/distributed-example.yaml)
- [Sample configuration file for single-node deployment with ODP](./example/single-with-obproxy-example.yaml)
- [Sample configuration file for three-node deployment with ODP](./example/distributed-with-obproxy-example.yaml)
- [Sample configuration file for three-node deployment with ODP and obagent](./example/obagent/distributed-with-obproxy-and-obagent-example.yaml)

This section describes how to start a local single-node OceanBase cluster by using the [sample configuration file for local single-node deployment in the small-scale deployment mode](./example/mini-local-example.yaml).

```shell
# Modify the working directory of the OceanBase cluster: home_path.
# Modify the SQL service protocol port of the OceanBase cluster: mysql_port. This port will be used to connect to the cluster later.
# Modify the internal communication port of the OceanBase cluster: rpc_port.
vi ./example/mini-local-example.yaml
```

If the target server to run the OceanBase cluster is not the logged-in server, do not use the `sample configuration file for local single-node deployment`. Use another configuration file.
Do not forget to change the user password at the beginning of the configuration file.

```yaml
user:
  username: <Your account name.>
  password: <Your logon password.>
  key_file: <The path of your private key.>
```

`username` specifies the username used to log on to the target server. Make sure that your username has the write permission on the `home_path` directory. `password` and `key_file` are used to authenticate the user. Generally, only one of them is required.
> **NOTE:** After you specify the path of the key, add an annotation to the `password` field or delete it if your key does not require a password. Otherwise, `password` will be deemed as the password of the key and used for login, leading to a logon verification failure.

### Step 2: Deploy and start a cluster

```shell
# The following command checks whether the home_path and data_dir directories are empty.
# If not, an error is returned. In this case, you can add the -f option to forcibly clear the directories.
obd cluster deploy lo -c local-example.yaml

# The following command checks whether the value of the fs.aio-max-nr parameter is no less than 1048576.
# Generally, you do not need to modify the fs.aio-max-nr parameter when you start one node on a server.
# However, you must modify the fs.aio-max-nr parameter when you start four or more nodes on a server.
obd cluster start lo
```

### Step 3: View the cluster status

```shell
# View clusters managed by OBD.
obd cluster list
# View the status of the lo cluster.
obd cluster display lo
```

### Step 4: Modify configurations

OceanBase Database has hundreds of configuration items and some of them are coupled. We recommend that you do not modify the configurations in the sample configuration file unless you are familiar with OceanBase Database. The following example shows how to modify the configurations and make them take effect.

```shell
# Run the edit-config command to enter the editing mode and modify the cluster configurations.
obd cluster edit-config lo
# Set the value of sys_bkgd_migration_retry_num to 5.
# Note that the minimum value of sys_bkgd_migration_retry_num is 3.
# Save the settings and exit. OBD will tell you how to make the modification take effect.
# To make the modification take effect, you only need to run the reload command.
obd cluster reload lo
```

### Step 5: Stop the cluster

You can run the `stop` command to stop a running cluster. If the `start` command fails but some processes are still running, run the `destroy` command to destroy the cluster.

```shell
obd cluster stop lo
```

### Step 6: Destroy the cluster

To destroy the cluster, run this command:

```shell
# When the start command fails, some processes may still be running.
# In this case, use the -f option to forcibly stop and destroy the cluster.
obd cluster destroy lo
```

## Other OBD commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

### Mirror and repository commands

#### `obd mirror clone`

Copy an RPM package to the local mirror repository. You can run the corresponding OBD cluster command to start the mirror.

```shell
obd mirror clone <path> [-f]
```

`path` specifies the path of the RPM package.

The `-f` option is `--force`. `-f` is optional. This option is disabled by default. If it is enabled and a mirror of the same name exists in the repository, the copied mirror will forcibly overwrite the existing one.

#### `obd mirror create`

Creates a mirror based on the local directory. When OBD starts a user-compiled open-source OceanBase software, you can run this command to add the compilation output to the local repository. Then, you can run the corresponding `obd cluster` command to start the mirror.

```shell
obd mirror create -n <component name> -p <your compile dir> -V <component version> [-t <tag>] [-f]
```

For example, you can [compile an OceanBase cluster based on the source code](https://open.oceanbase.com/docs/community/oceanbase-database/V3.1.0/get-the-oceanbase-database-by-using-source-code). Then, you can run the `make DESTDIR=./ install && obd mirror create -n oceanbase-ce -V 3.1.0 -p ./usr/local` command to add the compilation output to the local repository of OBD.

This table describes the corresponding options.

| Option | Required | Data type | Description |
--- | --- | --- |---
| -n/--name | Yes | string | The component name. If you want to compile an OceanBase cluster, set this option to oceanbase-ce. If you want to compile ODP, set this option to obproxy.  |
| -p/--path | Yes | string | The directory that stores the compilation output. OBD will automatically retrieve files required by the component from this directory.  |
| -V/--version | Yes | string | The component version.  |
| -t/--tag | No | string | The mirror tags. You can define one or more tags for the created mirror. Separate multiple tags with commas (,).  |
| -f/--force | No | bool | Specifies whether to forcibly overwrite an existing mirror or tag. This option is disabled by default.  |

#### `obd mirror list`

Shows the mirror repository or mirror list.

```shell
obd mirror list [mirror repo name]
```

`mirror repo name` specifies the mirror repository name. This parameter is optional. When it is not specified, all mirror repositories will be returned. When it is specified, only the specified mirror repository will be returned.

#### `obd mirror update`

Synchronizes the information of all remote mirror repositories.

```shell
obd mirror update
```

### Cluster commands

A deployment configuration is the minimum unit for OBD cluster commands. A deployment configuration is a `yaml` file. It contains all configuration information of a deployment, including the server login information, component information, component configuration information, and component server list.

To start a cluster by using OBD, you must register the deployment configuration of your cluster to OBD. You can run the `obd cluster edit-config` command to create an empty deployment configuration or run the `obd cluster deploy -c config` command to import a deployment configuration.

#### `obd cluster autodeploy`

When you pass a simple configuration file to OBD, OBD will automatically generate a complete configuration file with the maximum specifications based on the resources of the target server, and then deploy and start a cluster on the target server.

```shell
obd cluster autodeploy <deploy name> -c <yaml path> [-f] [-U] [-A] [-s]
```

`deploy name` specifies the name of the deployment configuration file.

The following table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- |---
| -c/--config | Yes | string | None | Specifies the yaml file used for deployment and registers the deployment configuration to OBD. <br>When the `deploy name` already exists, OBD will check the status of the existing deployment configuration. If the existing deployment configuration has not been applied, it will be overwritten. If the existing deployment configuration is in use, an error will be returned.  |
| -f/--force | No | bool | false | Specifies whether to forcibly clear the working directory. <br>When the component requires an empty working directory but this option is disabled, an error will be returned if the working directory is not empty.  |
| -U/--ulp/--unuselibrepo | No | bool | false | Specifies whether to prevent OBD from automatically taking actions when dependencies are missing. If this option is disabled and OBD detects that some dependencies are missing, OBD will automatically search for the corresponding libs mirrors and install them. If this option is enabled, the **unuse_lib_repository: true** field will be added to the corresponding configuration file. You can also add the **unuse_lib_repository: true** field to the configuration file to enable this option.  |
| -A/--act/--auto-create-tenant | No | bool | false | Specifies whether to enable OBD to create the `test` tenant during the bootstrap by using all available resources of the cluster. If this option is enabled, the **auto_create_tenant: true** field will be added to the corresponding configuration file. You can also add the **auto_create_tenant: true** field to the configuration file to enable this option.  |
| -s/--strict-check | No | bool | false | Specifies whether to return an error and directly exit the process when the component pre-check fails. If this option is disabled, OBD will return an error but not forcibly end the process when pre-check fails. We recommend that you enable this option to avoid startup failures due to insufficient resources.  |

#### `obd cluster edit-config`

Modifies a deployment configuration or creates one when the specified deployment configuration does not exist.

```shell
obd cluster edit-config <deploy name>
```

`deploy name` specifies the name for the deployment configuration file.

#### `obd cluster deploy`

Deploys a cluster based on the deployment configuration file. Based on the deployment configuration file, this command finds the matching mirror, then installs the mirror in a local repository. This process is called local installation.
Then, OBD distributes the components of the required version in the local repository to the target server. This process is called remote installation.
During both local and remote installation, OBD checks whether the server stores dependencies required for running the components.
This command allows you to deploy a cluster based on a deployment configuration that has been registered to OBD or by passing a `yaml` file.

```shell
obd cluster deploy <deploy name> [-c <yaml path>] [-f] [-U] [-A]
```

`deploy name` specifies the name of the deployment configuration file.

The following table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- |---
| -c/--config | No | string | None | Specifies the yaml file used for deployment and registers the deployment configuration to OBD. <br>If this option is enabled and a deployment configuration of the specified `deploy name` already exists, the existing deployment configuration will be overwritten. <br>If this option is not enabled, OBD will search for the registered deployment configuration of the specified `deploy name`.  |
| -f/--force | No | bool | false | Specifies whether to forcibly clear the working directory. <br>When the component requires an empty working directory but this option is disabled, an error will be returned if the working directory is not empty.  |
| -U/--ulp/--unuselibrepo | No | bool | false | Specifies whether to prevent OBD from automatically taking actions when dependencies are missing. If this option is disabled and OBD detects that some dependencies are missing, OBD will automatically search for the corresponding libs mirrors and install them. If this option is enabled, the **unuse_lib_repository: true** field will be added to the corresponding configuration file. You can also add the **unuse_lib_repository: true** field to the configuration file to enable this option.  |
| -A/--act/--auto-create-tenant | No | bool | false | Specifies whether to enable OBD to create the `test` tenant during the bootstrap by using all available resources of the cluster. If this option is enabled, the **auto_create_tenant: true** field will be added to the corresponding configuration file. You can also add the **auto_create_tenant: true** field to the configuration file to enable this option.  |

#### `obd cluster start`

Starts a deployed cluster. If the cluster is started, OBD will return its status.

```shell
obd cluster start <deploy name> [-s]
```

`deploy name` specifies the name of the deployment configuration file.

`-s` is `--strict-check`. `-s` specifies whether to return an error and directly exit the process when the component pre-check fails. If this option is disabled, OBD will return an error but not forcibly end the process when pre-check fails. We recommend that you enable this option to avoid startup failures due to insufficient resources. `-s` is optional. Its data type is `bool`. This option is disabled by default.

#### `obd cluster list`

Shows the status of all clusters that have been registered to OBD. The cluster names are specified by the deploy name parameter.

```shell
obd cluster list
```

#### `obd cluster display`

Shows the status of the specified cluster.

```shell
obd cluster display <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

#### `obd cluster reload`

Reloads a running cluster. After you modify the configuration information of a running cluster by using the `edit-config` command, you can run the `reload` command to let your modification take effect.
> **NOTE:** Some configuration items may not take effect after you run the `reload` command. You need to restart or even redeploy the cluster for these configuration items to take effect.

Do operations based on the result returned by the `edit-config` command.

```shell
obd cluster reload <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

#### `obd cluster restart`

Restarts a running cluster. After you run the edit-config command to modify the configuration information of a running cluster, you can run the `restart` command for the modification to take effect.

> **NOTE:** Some configuration items may not take effect after you run the `restart` command. You even need to redeploy the cluster for some configuration items to take effect.

Perform operations based on the result returned by the edit-config command.

```shell
obd cluster restart <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

#### `obd cluster redeploy`

Redeploys a running cluster. After you run the `edit-config` command to modify the configuration information of a running cluster, you can run the `redeploy` command to let your modification take effect.

> **NOTE:** This command destroys the cluster and redeploys it. Data in the cluster will be lost. Please back up the data before you run this command.

```shell
obd cluster redeploy <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

#### `obd cluster stop`

Stops a running cluster.

```shell
obd cluster stop <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

#### `obd cluster destroy`

Destroys a deployed cluster. If the cluster is running, this command stops the cluster before destroying it.

```shell
obd cluster destroy <deploy name> [-f]
```

`deploy name` specifies the name of the deployment configuration file.

`-f` is `--force-kill`. This option specifies whether to forcibly stop running processes in the working directory. Before OBD destroys the cluster, it will check for running processes. These processes may result from the failure of the **start** command. They may also belong to other clusters when configurations of this cluster overlap with those of other clusters. If an ongoing process is found in the working directory, OBD will stop the **destroy** command. However, if this option is enabled, OBD will forcibly stop the ongoing processes and run the **destroy** command. `-f` is optional. Its data type is `bool`. This option is disabled by default.

#### `obd cluster tenant create`

Creates a tenant. This command applies only to an OceanBase cluster. This command automatically creates resource units and resource pools.

```shell
obd cluster tenant create <deploy name> [-n <tenant name>] [flags]
```

`deploy name` specifies the name of the deployment configuration file.

This table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -n/--tenant-name | No | string | test | The tenant name. OBD will automatically generate resource units and resource pools with unique names based on the tenant name.  |
| --max-cpu | No | float | 0 | The maximum number of CPU cores available for the tenant. When this option is set to 0, all available CPU cores of the cluster can be used by the tenant.  |
| --min-cpu | No | float | 0 | The minimum number of CPU cores available for the tenant. When this option is set to 0, the minimum number of CPU cores is the same as the maximum number of CPU cores.  |
| --max-memory | No | int | 0 | The maximum memory capacity available for the tenant. When this option is set to 0, all available memory capacity of the cluster can be used by the tenant. When the actual value is less than 1 GB, an error is returned.  |
| --min-memory | No | int | 0 | The minimum memory capacity available for the tenant. When this option is set to 0, the minimum memory capacity is the same as the maximum memory capacity.  |
| --max-disk-size | No | int | 0 | The maximum disk space available for the tenant. When this option is set to 0, all available disk space of the cluster can be used by the tenant. If the actual value is less than 512 MB, an error is returned.  |
| --max-iops | No | int | 128 | The maximum IOPS for the tenant. Value range: [128, +∞).  |
| --min-iops | No | int | 0 | The minimum IOPS for the tenant. Value range: [128, +∞). When this option is set to 0, the minimum IOPS is the same as the maximum IOPS.  |
| --max-session-num | No | int | 64 | The maximum number of sessions allowed for the tenant. Value range: [64, +∞).  |
| --unit-num | No | int | 0 | The number of units to be created in a zone. It must be less than the number of OBServers in the zone. When this option is set to 0, the maximum value is used.  |
| -z/--zone-list | No | string |   | Specifies the list of zones of the tenant. Separate multiple zones with commas (,). If this option is not specified, all zones of the cluster are included.  |
| --primary-zone | No | string | RANDOM | The primary zone of the tenant.  |
| --charset | No | string |   | The character set of the tenant.  |
| --collate | No | string |   | The collation of the tenant.  |
| --replica-num | No | int | 0 | The number of replicas of the tenant. When this option is set to 0, the number of replicas is the same as that of zones.  |
| --logonly-replica-num | No | string | 0 | The number of log replicas of the tenant. When this option is set to 0, the number of log replicas is the same as that of replicas.  |
| --tablegroup | No | string |   | The default table group of the tenant. |
| --locality | No | string |   | The distribution status of replicas across zones. For example, F@z1,F@z2,F@z3,R@z4 means that z1, z2, and z3 are full-featured replicas and z4 is a read-only replica.  |
| -s/--variables | No | string | ob_tcp_invited_nodes='%' | The system variables of the tenant.  |

#### `obd cluster tenant drop`

Deletes a tenant. This command applies only to an OceanBase cluster. This command automatically deletes the corresponding resource units and resource pools.

```shell
obd cluster tenant drop <deploy name> [-n <tenant name>]
```

`deploy name` specifies the name of the deployment configuration file.

`-n` is `--tenant-name`. This option specifies the name of the tenant to be deleted. This option is required.

### Testing commands

#### `obd test mysqltest`

Runs the mysqltest on the specified node of an OcecanBase cluster or ODP. To run the mysqltest, you must install OBClient.

```shell
obd test mysqltest <deploy name> [--test-set <test-set>] [flags]
```

`deploy name` specifies the name of the deployment configuration file.

This table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -c/--component | No | string |   | The name of the component to be tested. Valid values: oceanbase-ce and obproxy. If this option is not specified, OBD will search for obproxy and oceanbase-ce in sequence. If obproxy is found, OBD will stop the search and use obproxy for the subsequent tests. If obproxy is not found, OBD will continue to search for oceanbase-ce.  |
| --test-server | No | string | The first node of the specified component.  | It must be the name of a node of the specified component.  |
| --mode | No | string | both | The test mode. Valid values: mysql and both.  |
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

#### `obd test sysbench`

Runs the Sysbench test on the specified node of an OcecanBase cluster or ODP.  To run the Sysbench test, you must install OBClient and ob-sysbench.

```shell
obd test sysbench <deploy name> [flags]
```

`deploy name` specifies the name of the deployment configuration file.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -c/--component | No | string |   | The name of the component to be tested. Valid values: oceanbase-ce and obproxy. If this option is not specified, OBD will search for obproxy and oceanbase-ce in sequence. If obproxy is found, OBD will stop the search and use obproxy for subsequent tests. If obproxy is not found, OBD will continue to search for oceanbase-ce.  |
| --test-server | No | string | The first node of the specified component.  | It must be the name of a node of the specified component.  |
| --user | No | string | root | The username for running the test.  |
| --password | No | string |   | The password for running the test.  |
| --tenant | No | string | test | The tenant name for running the test.  |
| --database | No | string | test | The cluster for performing the test.  |
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
| --rand-type | No | string | The random number generation function used for data access. Valid values: special, uniform, gaussian, and pareto.  Default value: special.  |
| ---skip-trx | No | string |   | Specifies whether to enable or disable a transaction in a read-only test.  |

## Q&A

### Q: How can I specify the version of a component?

A: You can add the version declaration to the deployment configuration file. For example, you can specify the version of OceanBase-CE V3.1.0 in the deployment configuration file in the following format:

```yaml
oceanbase-ce:
  version: 3.1.0
```

### Q: How can I use a component of a specific version?

A: You can add the package_hash or tag declaration to the deployment configuration file.
For example, if you have tagged your compiled OceanBase-CE, you can specify it by tag. For example:

```yaml
oceanbase-ce:
  tag: my-oceanbase
```

You can also use package_hash to specify a specific version. When you run an `obd mirror` command, OBD will return an MD5 value of the component. The MD5 value is the value of package_hash.

```yaml
oceanbase-ce:
  package_hash: 929df53459404d9b0c1f945e7e23ea4b89972069
```

### Q: How can I modify the startup process after I modify the code of OceanBase-CE?

A: You can modify the startup plug-ins in the `~/.obd/plugins/oceanbase-ce/` directory. For example, after you add a new startup configuration item for OceanBase-CE V3.1.0, you can modify the `start.py` file in the `~/.obd/plugins/oceanbase-ce/3.1.0` directory.

## Protocol

OBD complies with [GPL-3.0](/LICENSE).
