# Start an OceanBase cluster

After you install OBD, you can run these commands as the root user to start a local single-node OceanBase cluster.
Before you run the commands, make sure that these conditions are met:

- You have logged on as the root user.
- Ports `2882` and `2883` are available.
- Your server has at least 8 GB of memory.
- Your server has at least 2 CPU cores.

> **NOTE:** If the preceding conditions are not met, see [Use OBD to start an OceanBase cluster](./start-OceanBase-cluster-with-obd.md).

> **NOTE:** For the convenience of using root here, OBD and OceanBase database do not have any restrictions on running users. We do not recommend that you use root in production.

```shell
obd cluster deploy c1 -c ./example/mini-local-example.yaml
obd cluster start c1
# Connect to the OceanBase Database by using a MySQL client.
mysql -h127.1 -uroot -P2883
```
