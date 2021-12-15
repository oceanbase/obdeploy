# 快速启动 OceanBase 数据库

安装 OBD 后，您可以使用 root 用户执行这组命令快速启动本地单节点 OceanBase 数据库。
在此之前您需要确认以下信息：

- 当前用户为 root。
- `2882` 和 `2883` 端口没有被占用。
- 您的机器内存应该不低于 8 G。
- 您的机器 CPU 数目应该不低于 2。

> **说明：** 如果以上条件不满足，请参考[使用 OBD 启动 OceanBase 数据库集群](./start-OceanBase-cluster-with-obd.md)。

> **注意：** 此处为了方便使用 root，OBD 和 OceanBase 数据库没有对运行用户做出任何限制，我们不建议生产中直接使用 root。

```shell
obd cluster deploy c1 -c ./example/mini-local-example.yaml
obd cluster start c1
# 使用 mysql 客户端链接到到 OceanBase 数据库。
mysql -h127.1 -uroot -P2883
```