# OceanBase Deployer

OceanBase Deployer（简称 OBD）是 OceanBase 开源软件的安装部署工具。OBD 同时也是包管理器，可以用来管理 OceanBase 所有的开源软件。本文介绍如何安装 OBD、使用 OBD 和 OBD 的命令。

## 安装 OBD

您可以使用以下方式安装 OBD：

### 方案1： 使用 RPM 包（Centos 7 及以上）安装

```shell
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://mirrors.aliyun.com/oceanbase/OceanBase.repo
sudo yum install -y ob-deploy
source /etc/profile.d/obd.sh
```

### 方案2：使用源码安装

使用源码安装 OBD 之前，请确认您已安装以下依赖：

- gcc
- wget
- python-devel
- openssl-devel
- xz-devel
- mysql-devel
  
Python2.7 使用以下命令安装：

```shell
sh rpm/build.sh build
source /etc/profile.d/obd.sh
```

Python3.8 使用以下命令安装：

首先在 Python 2.7 环境下执行以下命令：

```shell
sh rpm/build.sh executer
```

然后在 Python3.8 环境执行以下命令：

```shell
rpm/build.sh build_obd
source /etc/profile.d/obd.sh
```

## 快速启动 OceanBase 数据库

安装 OBD 后，您可以使用 root 用户执行这组命令快速启动本地单节点 OceanBase 数据库。
在此之前您需要确认以下信息：

- 当前用户为 root。
- `2882` 和 `2883` 端口没有被占用。
- 您的机器内存应该不低于 8 G。
- 您的机器 CPU 数目应该不低于 2。

> **说明：** 如果以上条件不满足，请参考[使用 OBD 启动 OceanBase 数据库集群](./docs/docs-cn/install-and-use/start-OceanBase-cluster-with-obd.md)。

> **注意：** 此处为了方便使用 root，OBD 和 OceanBase 数据库没有对运行用户做出任何限制，我们不建议生产中直接使用 root。

```shell
obd cluster deploy c1 -c ./example/mini-local-example.yaml
obd cluster start c1
# 使用 mysql 客户端链接到到 OceanBase 数据库。
mysql -h127.1 -uroot -P2883
```

## 使用 OBD 启动 OceanBase 数据库集群

如何使用 OBD 启动 OceanBase 数据库集群，请参考文档[使用 OBD 启动 OceanBase 数据库集群](./docs/docs-cn/install-and-use/start-OceanBase-cluster-with-obd.md)

## 其他 OBD 命令

OBD 有多级命令，您可以在每个层级中使用 `-h/--help` 选项查看子命令的帮助信息。

- [镜像和仓库命令组](./docs/docs-cn/obd-commands/mirror-and-repository-commands.md)
- [集群命令组](./docs/docs-cn/obd-commands/cluster-commands.md)
- [测试命令组](./docs/docs-cn/obd-commands/testing-commands.md)

## Q&A

### Q: 如何指定使用组件的版本？

A: 在部署配置文件中使用版本声明。例如，如果您使用的是 OceanBase-CE 3.1.0 版本，可以指定以下配置：

```yaml
oceanbase-ce:
  version: 3.1.0
```

### Q: 如何指定使用特定版本的组件？

A: 在部署配置文件中使用 package_hash 或 tag 声明。
如果您给自己编译的 OceanBase-CE 设置了 tag，您可以使用 tag 来指定。如：

```yaml
oceanbase-ce:
  tag: my-oceanbase
```

您也可以通过 package_hash 来指定特定的版本。当您使用 `obd mirror` 相关命令时会打印出组件的 md5 值，这个值即为 package_hash。

```yaml
oceanbase-ce:
  package_hash: 929df53459404d9b0c1f945e7e23ea4b89972069
```

### Q：我修改了 OceanBase-CE 了代码，需要修改启动流程怎么办？

A：您可以修改 `~/.obd/plugins/oceanbase-ce/` 下的启动相关插件。比如您为 3.1.0 版本的 OceanBase-CE 添加了一个新的启动配置，可以修改 `~/.obd/plugins/oceanbase-ce/3.1.0/start.py`。

### Q：如何升级 OBD？

A：您可以使用 `obd update` 命令升级 OBD。当您升级完成后可以使用命令 `obd --version` 查看版本，确认是否升级成功。

## 协议

OBD 采用 [GPL-3.0](./LICENSE) 协议。
