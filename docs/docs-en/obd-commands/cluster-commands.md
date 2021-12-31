# Cluster commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

A deployment configuration is the minimum unit for OBD cluster commands. A deployment configuration is a `yaml` file. It contains all configuration information of a deployment, including the server login information, component information, component configuration information, and component server list.

To start a cluster by using OBD, you must register the deployment configuration of your cluster to OBD. You can run the `obd cluster edit-config` command to create an empty deployment configuration or run the `obd cluster deploy -c config` command to import a deployment configuration.

## `obd cluster autodeploy`

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
| -s/--strict-check | No | bool | false | Some components will do relevant checks before starting. It will issue an alarm when the check fails, but it will not force the process to stop. Using this option can return an error and directly exit the process when the component pre-check fails. We recommend that you enable this option to avoid startup failures due to insufficient resources.  |

## `obd cluster edit-config`

Modifies a deployment configuration or creates one when the specified deployment configuration does not exist.

```shell
obd cluster edit-config <deploy name>
```

`deploy name` specifies the name for the deployment configuration file.

## `obd cluster deploy`

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

## `obd cluster start`

Starts a deployed cluster. If the cluster is started, OBD will return its status.

```shell
obd cluster start <deploy name> [flags]
```

`deploy name` specifies the name of the deployment configuration file.

This table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -s/--servers | No | string |   | A list of machines, followed by the `name` value corresponding to `servers` in the `yaml` file, separated by `,`. Be used for specifying the start-up machines. If this option is disabled, all machines under the component will start without executing bootstrap.  |
| -c/--components | No | string |   | A list of components, separated by `,`. Be used for specifying the start-up components. If this option is disabled, all machines under the component will start without entering the running state.  |
| --wop/--without-parameter | No | bool | false | Start without parameters. The node does not respond to this option when this node is starting for the first time.  |
| -S/--strict-check | No | bool | false | Some components will do relevant checks before starting. OBD will throw an error when the check fails, but OBD will not force the process to stop. Using this option can return an error and directly exit the process when the component pre-check fails. We recommend that you enable this option to avoid startup failures due to insufficient resources.  |

## `obd cluster list`

Shows the status of all clusters that have been registered to OBD. The cluster names are specified by the deploy name parameter.

```shell
obd cluster list
```

## `obd cluster display`

Shows the status of the specified cluster.

```shell
obd cluster display <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

## `obd cluster reload`

Reloads a running cluster. After you modify the configuration information of a running cluster by using the `edit-config` command, you can run the `reload` command to let your modification take effect.

> **NOTE:** Some configuration items may not take effect after you run the `reload` command. You need to restart or even redeploy the cluster for these configuration items to take effect. Do operations based on the result returned by the `edit-config` command.

```shell
obd cluster reload <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

## `obd cluster restart`

Restarts a running cluster. By default, OBD restarts without any parameters. After you run the edit-config command to modify the configuration information of a running cluster, you can run the `restart` command for the modification to take effect.

> **NOTE:** Some configuration items may not take effect after you run the `restart` command. You even need to redeploy the cluster for some configuration items to take effect. Perform operations based on the result returned by the edit-config command.

```shell
obd cluster restart <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

This table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -s/--servers | No | string |   | A list of machines, followed by the `name` value corresponding to `servers` in the `yaml` file, separated by `,`.  |
| -c/--components | No | string |   | A list of components, separated by `,`. Be used for specifying the start-up components. If this option is disabled, all machines under the component will start without entering the running state.  |
| --wp/--with-parameter | No | bool | false | Restarts OBD with parameters. This option makes the parameters valid when you restart OBD.   |

## `obd cluster redeploy`

Redeploys a running cluster. After you run the `edit-config` command to modify the configuration information of a running cluster, you can run the `redeploy` command to let your modification take effect.

> **NOTE:** This command destroys the cluster and redeploys it. Data in the cluster will be lost. Please back up the data before you run this command.

```shell
obd cluster redeploy <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

## `obd cluster stop`

Stops a running cluster.

```shell
obd cluster stop <deploy name>
```

`deploy name` specifies the name of the deployment configuration file.

This table describes the corresponding options.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- | ---
| -s/--servers | No | string |   | A list of machines, followed by the `name` value corresponding to `servers` in the `yaml` file, separated by `,`. Be used for specifying the start-up machines.  |
| -c/--components | No | string |   | A list of components, separated by `,`. Be used for specifying the start-up components. If not all components under the configuration start, this configuration will not enter the stopped state.  |

## `obd cluster destroy`

Destroys a deployed cluster. If the cluster is running state, this command will first try to execute `stop` and then `destroy` after success.

```shell
obd cluster destroy <deploy name> [-f]
```

`deploy name` specifies the name of the deployment configuration file.

`-f` is `--force-kill`. This option specifies whether to forcibly stop running processes in the working directory. Before OBD destroys the cluster, it will check for running processes. These processes may result from the failure of the **start** command. They may also belong to other clusters when configurations of this cluster overlap with those of other clusters. If an ongoing process is found in the working directory, OBD will stop the **destroy** command. However, if this option is enabled, OBD will forcibly stop the ongoing processes and run the **destroy** command. `-f` is optional. Its data type is `bool`. This option is disabled by default.

## `obd cluster upgrade`

Update a running component.

```shell
obd cluster upgrade <deploy_name> -c <component_name> -V <version> [tags]
```

`deploy name` specifies the name of the deployment configuration file.

| Option | Required | Data type | Default value | Description |
--- | --- | --- |--- |---
-c/--component | Yes | string | empty | The component name you want to upgrade.
-V/--version | Yes | string | The target upgrade version number.
--skip-check | No | bool | false | Skip check.
--usable | No | string | empty | The hash list for the mirrors that you use during upgrade. Separated with `,`.
--disable | No | string | empty | The hash list for the mirrors that you disable during upgrade. Separated with `,`.
-e/--executer-path | No | string | /usr/obd/lib/executer | The executer path for the upgrade script.

## `obd cluster tenant create`

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

## `obd cluster tenant drop`

Deletes a tenant. This command applies only to an OceanBase cluster. This command automatically deletes the corresponding resource units and resource pools.

```shell
obd cluster tenant drop <deploy name> [-n <tenant name>]
```

`deploy name` specifies the name of the deployment configuration file.

`-n` is `--tenant-name`. This option specifies the name of the tenant to be deleted. This option is required.
