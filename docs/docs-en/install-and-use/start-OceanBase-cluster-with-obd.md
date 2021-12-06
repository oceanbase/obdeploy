# Use OBD to start an OceanBase cluster

To start an OceanBase cluster, follow these steps:

### Step 1: Select a configuration file

Select a configuration file based on your resource configurations:

#### Small-scale deployment mode

This deployment mode applies to personal devices with at least 8 GB of memory.

- [Sample configuration file for local single-node deployment](../../../example/mini-local-example.yaml)
- [Sample configuration file for single-node deployment](../../../example/mini-single-example.yaml)
- [Sample configuration file for three-node deployment](../../../example/mini-distributed-example.yaml)
- [Sample configuration file for single-node deployment with ODP](../../../example/mini-single-with-obproxy-example.yaml)
- [Sample configuration file for three-node deployment with ODP](../../../example/mini-distributed-with-obproxy-example.yaml)

#### Professional deployment mode

This deployment mode applies to advanced Elastic Compute Service (ECS) instances or physical servers with at least 16 CPU cores and 64 GB of memory.

- [Sample configuration file for local single-node deployment](../../../example/local-example.yaml)
- [Sample configuration file for single-node deployment](../../../example/single-example.yaml)
- [Sample configuration file for three-node deployment](../../../example/distributed-example.yaml)
- [Sample configuration file for single-node deployment with ODP](../../../example/single-with-obproxy-example.yaml)
- [Sample configuration file for three-node deployment with ODP](../../../example/distributed-with-obproxy-example.yaml)
- [Sample configuration file for three-node deployment with ODP and obagent](../../../example/obagent/distributed-with-obproxy-and-obagent-example.yaml)

This section describes how to start a local single-node OceanBase cluster by using the [sample configuration file for local single-node deployment in the small-scale deployment mode](../../../example/mini-local-example.yaml).

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
