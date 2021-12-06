# 使用 OBD 启动 OceanBase 数据库集群

按照以下步骤启动 OceanBase 数据库集群：

## 第 1 步. 选择配置文件

根据您的资源条件选择正确的配置文件：

### 小规格开发模式

适用于个人设备（内存不低于 8G）。

- [本地单节点配置样例](../../../example/mini-local-example.yaml)
- [单节点配置样例](../../../example/mini-single-example.yaml)
- [三节点配置样例](../../../example/mini-distributed-example.yaml)
- [单节点 + ODP 配置样例](../../../example/mini-single-with-obproxy-example.yaml)
- [三节点 + ODP 配置样例](../../../example/mini-distributed-with-obproxy-example.yaml)

### 专业开发模式

适用于高配置 ECS 或物理服务器（不低于 16 核 64G 内存）。  

- [本地单节点配置样例](../../../example/local-example.yaml)
- [单节点配置样例](../../../example/single-example.yaml)
- [三节点配置样例](../../../example/distributed-example.yaml)
- [单节点 + ODP 配置样例](../../../example/single-with-obproxy-example.yaml)
- [三节点 + ODP 配置样例](../../../example/distributed-with-obproxy-example.yaml)
- [三节点 + ODP + obagent 配置样例](../../../example/obagent/distributed-with-obproxy-and-obagent-example.yaml)

本文以 [小规格开发模式-本地单节点](../../../example/mini-local-example.yaml) 为例，启动一个本地单节点的 OceanBase 数据库。

```shell
# 修改 OceanBase 数据库的工作目录 home_path。
# 修改 OceanBase 数据库 SQL 服务协议端口号 mysql_port。后续将使用此端口连接数据库。
# 修改 OceanBase 数据库集群内部通信的端口号 rpc_port。
vi ./example/mini-local-example.yaml
```

如果您的目标机器（OceanBase 数据库程序运行的机器）不是当前机器，请不要使用 `本地单节点配置样例`，改用其他样例。
同时您还需要修改配置文件顶部的用户密码信息。

```yaml
user:
  username: <您的账号名>
  password: <您的登录密码>
  key_file: <您的私钥路径>
```

`username` 为登录到目标机器的用户名，确保您的用户名有 `home_path` 的写权限。`password` 和 `key_file` 均用于验证用户，通常情况下只需要填写一个。

> **注意：** 在配置秘钥路径后，如果您的秘钥不需要口令，请注释或者删除 `password`，以免 `password` 被视为秘钥口令用于登录，导致校验失败。

## 第 2 步. 部署和启动数据库

```shell
# 此命令会检查 home_path 和 data_dir 指向的目录是否为空。
# 若目录不为空，则报错。此时可以加上 -f 选项，强制清空。
obd cluster deploy lo -c local-example.yaml

# 此命令会检查系统参数 fs.aio-max-nr 是否不小于 1048576。
# 通常情况下一台机器启动一个节点不需要修改 fs.aio-max-nr。
# 当一台机器需要启动 4 个及以上的节点时，请务必修改 fs.aio-max-nr。
obd cluster start lo 
```

## 第 3 步. 查看集群状态

```shell
# 参看 OBD 管理的集群列表
obd cluster list
# 查看 lo 集群状态
obd cluster display lo
```

## 第 4 步. 修改配置

OceanBase 数据库有数百个配置项，有些配置是耦合的，在您熟悉 OceanBase 数据库之前，不建议您修改示例配件文件中的配置。此处示例用来说明如何修改配置，并使之生效。

```shell
# 使用 edit-config 命令进入编辑模式，修改集群配置
obd cluster edit-config lo
# 修改 sys_bkgd_migration_retry_num 为 5
# 注意 sys_bkgd_migration_retry_num 值最小为 3
# 保存并退出后，OBD 会告知您如何使得此次改动生效
# 此配置项仅需要 reload 即可生效
obd cluster reload lo
```

## 第 5 步. 停止集群

`stop` 命令用于停止一个运行中的集群。如果 `start` 命令执行失败，但有进程没有退出，请使用 `destroy` 命令。

```shell
obd cluster stop lo
```

## 第 6 步. 销毁集群

运行以下命令销毁集群：

```shell
# 启动集群时失败，可以能会有一些进程停留。
# 此时可用 -f 选项强制停止并销毁集群
obd cluster destroy lo
```
