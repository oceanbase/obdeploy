# OceanBase Deploy

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

**OceanBase Deploy** （简称 OBD）是 OceanBase 开源软件的安装部署工具。OBD 同时也是包管理器，可以用来管理 OceanBase 所有的开源软件。本文介绍如何安装 OBD、使用 OBD 和 OBD 的命令。

## 安装 OBD

您可以使用以下方式安装 OBD：

### 方案1： 使用 RPM 包（Centos 7 及以上）安装。

  ```shell
  sudo yum install -y yum-utils
  sudo yum-config-manager --add-repo http://yum.tbsite.net/mirrors/oceanbase/OceanBase.repo
  sudo yum install -y ob-deploy
  source /etc/profile.d/obd.sh
  ```

### 方案2：使用源码安装。

  使用源码安装 OBD 之前，请确认您已安装以下依赖：

  - gcc
  - python-devel
  - openssl-devel
  - xz-devel
  - mysql-devel
  
  Python2 使用以下命令安装：

  ```shell
  pip install -r requirements.txt
  sh build.sh
  source /etc/profile.d/obd.sh
  ```

  Python3 使用以下命令安装：

  ```shell
  pip install -r requirements3.txt
  sh build.sh
  source /etc/profile.d/obd.sh
  ```

## 快速启动 OceanBase 数据库

安装 OBD 后，您可以使用 root 用户执行这组命令快速启动本地单节点 OceanBase 数据库。
在此之前您需要确认以下信息：

- 当前用户为 root。
- `2881` 和 `2882` 端口没有被占用。
- 您的机器内存应该不低于 8G。
- 您的机器 CPU 数目应该不低于 2。

> **说明：** 如果以上条件不满足，请移步[使用 OBD 启动 OceanBase 数据库集群](#使用-obd-启动-oceanbase-数据库集群)。

```shell
obd cluster deploy c1 -c ./example/mini-local-example.yaml
obd cluster start c1
# 使用 mysql 客户端链接到到 OceanBase 数据库。
mysql -h127.1 -uroot -P2881
```

## 使用 OBD 启动 OceanBase 数据库集群

按照以下步骤启动 OceanBase 数据库集群：

### 第 1 步. 选择配置文件

根据您的资源条件选择正确的配置文件：

#### 小规格开发模式

适用于个人设备（内存不低于 8G）。

- [本地单节点配置样例](./example/mini-local-example.yaml)
- [单节点配置样例](./example/mini-single-example.yaml)
- [三节点配置样例](./example/mini-distributed-example.yaml)
- [单节点 + ODP 配置样例](./example/mini-single-with-obproxy-example.yaml)
- [三节点 + ODP 配置样例](./example/mini-distributed-with-obproxy-example.yaml)

#### 专业开发模式

适用于高配置 ECS 或物理服务器（不低于 16 核 64G 内存）。  

- [本地单节点配置样例](./example/local-example.yaml)
- [单节点配置样例](./example/single-example.yaml)
- [三节点配置样例](./example/distributed-example.yaml)
- [单节点 + ODP 配置样例](./example/single-with-obproxy-example.yaml)
- [三节点 + ODP 配置样例](./example/distributed-with-obproxy-example.yaml)

本文以 [小规格开发模式-本地单节点](./example/mini-local-example.yaml) 为例，启动一个本地单节点的 OceanBase 数据库。

```shell
# 修改 home_path， 这是 OceanBase 数据库的工作目录。
# 修改 mysql_port，这是 OceanBase 数据库 SQL 服务协议端口号。后续将使用此端口连接数据库。
# 修改 rpc_port，这是 OceanBase 数据库集群内部通信的端口号。
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
`username` 为登录到目标机器的用户名，确保您的用户名有 `home_path` 的写权限。`password`和`key_file`都是用于验证改用户的方式，通常情况下只需要填写一个。
> **注意：** 在配置秘钥路径后，如果您的秘钥不需要口令，请注释或者删掉`password`，以免`password`被视为秘钥口令用于登录，导致校验失败。

### 第 2 步. 部署和启动数据库

```shell
# 此命令会检查 home_path 和 data_dir 指向的目录是否为空。
# 若目录不为空，则报错。此时可以加上 -f 选项，强制清空。
obd cluster deploy lo -c local-example.yaml

# 此命令会检查系统参数 fs.aio-max-nr 是否不小于 1048576。
# 通常情况下一台机器启动一个节点不需要修改 fs.aio-max-nr。
# 当一台机器需要启动 4 个及以上的节点时，请务必修改 fs.aio-max-nr。
obd cluster start lo 
```

### 第 3 步. 查看集群状态

```shell
# 参看obd管理的集群列表
obd cluster list
# 查看 lo 集群状态
obd cluster disply lo
```

### 第 4 步. 修改配置

OceanBase 数据库有数百个配置项，有些配置是耦合的，在您熟悉 OceanBase 数据库之前，不建议您修改示例配件文件中的配置。此处示例用来说明如何修改配置，并使之生效。

```shell
# 使用 edit-config 命令进入编辑模式，修改集群配置
obd cluster edit-config lo
# 修改 sys_bkgd_migration_retry_num 为 5
# 注意 sys_bkgd_migration_retry_num 值最小为 3
# 保存并退出后，obd 会告知您如何使得此次改动生效
# 此配置项仅需要 reload 即可生效
obd cluster reload lo
```

### 第 5 步. 停止集群

`stop` 命令用于停止一个运行中的集群。如果 `start` 命令执行失败，但有进程没有退出，请使用 `destroy` 命令。

```shell
obd cluster stop lo
```

### 第 6 步. 销毁集群

运行以下命令销毁集群：

```shell
# 启动集群时失败，可以能会有一些进程停留。
# 此时可用 -f 选项强制停止并销毁集群
obd cluster destroy lo
```

## 其他 OBD 命令

**OBD** 有多级命令，您可以在每个层级中使用 `-h/--help` 选项查看该子命令的帮助信息。

### 镜像和仓库命令组

#### `obd mirror clone`

将本地 RPM 包添加为镜像，之后您可以使用 **OBD 集群** 中相关的命令中启动镜像。

```shell
obd mirror clone <path> [-f]
```

参数 `path` 为 RPM 包的路径。

选项 `-f` 为 `--force`。`-f` 为可选选项。默认不开启。开启时，当镜像已经存在时，强制覆盖已有镜像。

#### `obd mirror create`

以本地目录为基础创建一个镜像。此命令主要用于使用 OBD 启动自行编译的 OceanBase 开源软件，您可以通过此命令将编译产物加入本地仓库，之后就可以使用 `obd cluster` 相关的命令启动它。

```shell
obd mirror create -n <component name> -p <your compile dir> -V <component version> [-t <tag>] [-f]
```
例如您根据 [OceanBase 编译指导书](https://open.oceanbase.com/docs/community/oceanbase-database/V3.1.0/get-the-oceanbase-database-by-using-source-code)编译成功后，可以使用 `make DESTDIR=./ install && obd mirror create -n oceanbase-ce -V 3.1.0 -p ./usr/local` 将编译产物加入OBD本地仓库。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 说明
--- | --- | --- |---
-n/--name | 是 | string | 组件名。如果您编译的是 OceanBase 数据库，则填写 oceanbase-ce。如果您编译的是 ODP，则填写 obproxy。
-p/--path | 是 | string | 编译目录。执行编译命令时的目录。OBD 会根据组件自动从该目录下获取所需的文件。
-V/--version | 是 | string | 版本号
-t/--tag | 否 | string | 镜像标签。您可以为您的创建的镜像定义多个标签，以英文逗号（,）间隔。
-f/--force | 否 | bool | 当镜像已存在，或者标签已存在时强制覆盖。默认不开启。

#### `obd mirror list`

显示镜像仓库或镜像列表

```shell
obd mirror list [mirror repo name]
```

参数 `mirror repo name` 为 镜像仓库名。该参数为可选参数。不填时，将显示镜像仓库列表。不为空时，则显示对应仓库的镜像列表。

#### `obd mirror update`

同步全部远程镜像仓库的信息

```shell
obd mirror update
```

### 集群命令组

OBD 集群命令操作的最小单位为一个部署配置。部署配置是一份 `yaml` 文件，里面包含各个整个部署的全部配置信息，包括服务器登录信息、组件信息、组件配置信息和组件服务器列表等。

在使用 OBD 启动一个集群之前，您需要先注册这个集群的部署配置到 OBD 中。您可以使用 `obd cluster edit-config` 创建一个空的部署配置，或使用 `obd cluster deploy -c config` 导入一个部署配置。

#### `obd cluster edit-config`

修改一个部署配置，当部署配置不存在时创建。

```shell
obd cluster edit-config <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

#### `obd cluster deploy`

根据配置部署集群。此命令会根据部署配置文件中组件的信息查找合适的镜像，并安装到本地仓库，此过程称为本地安装。
在将本地仓库中存在合适版本的组件分发给目标服务器，此过程称为远程安装。
在本地安装和远程安装时都会检查服务器是否存在组件运行所需的依赖。
此命令可以直接使用 OBD 中已注册的 `deploy name` 部署，也可以通过传入 `yaml` 的配置信息。

```shell
obd cluster deploy <deploy name> [-c <yaml path>] [-f] [-U]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- |---
-c/--config | 否 | string | 无 | 使用指定的 yaml 文件部署，并将部署配置注册到 OBD 中。<br>当`deploy name` 存在时覆盖配置。<br>如果不使用该选项，则会根据 `deploy name` 查找已注册到OBD中的配置信息。
-f/--force | 否 | bool | false | 开启时，强制清空工作目录。<br>当组件要求工作目录为空且不使用改选项时，工作目录不为空会返回错误。
-U/--ulp/ --unuselibrepo | 否 | bool | false | 使用该选项将禁止 OBD 自动处理依赖。不开启的情况下，OBD 将在检查到缺失依赖时搜索相关的 libs 镜像并安装。使用该选项将会在对应的配置文件中天 **unuse_lib_repository: true**。也可以在配置文件中使用 **unuse_lib_repository: true** 开启。

#### `obd cluster start`

启动已部署的集群，成功时打印集群状态。

```shell
obd cluster start <deploy name> [-s]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项 `-s` 为 `--strict-check`。部分组件在启动前会做相关的检查，当检查不通过的时候会报警告，不会强制停止流程。使用该选项可开启检查失败报错直接退出。建议开启，可以避免一些资源不足导致的启动失败。非必填项。数据类型为 `bool`。默认不开启。

#### `obd cluster list`

显示当前 OBD 内注册的全部集群（deploy name）的状态。

```shell
obd cluster list
```

#### `obd cluster display`

展示指定集群的状态。

```shell
obd cluster display <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

#### `obd cluster reload`

重载一个运行中集群。当您使用 edit-config 修改一个运行的集群的配置信息后，可以通过 `reload` 命令应用修改。
需要注意的是，并非全部的配置项都可以通过 `reload` 来应用。有些配置项需要重启集群，甚至是重部署集群才能生效。
请根据 edit-config 后返回的信息进行操作。

```shell
obd cluster reload <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

#### `obd cluster restart`

重启一个运行中集群。当您使用 edit-config 修改一个运行的集群的配置信息后，可以通过 `restart` 命令应用修改。

> **注意：** 并非所有的配置项都可以通过 `restart` 来应用。有些配置项需要重部署集群才能生效。

请根据 edit-config 后返回的信息进行操作。

```shell
obd cluster restart <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。


#### `obd cluster redeploy`

重启一个运行中集群。当您使用 edit-config 修改一个运行的集群的配置信息后，可以通过 `redeploy` 命令应用修改。

> **注意：** 该命令会销毁集群，重新部署，您集群中的数据会丢失，请先做好备份。

```shell
obd cluster redeploy <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

#### `obd cluster stop`

停止一个运行中的集群。

```shell
obd cluster stop <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

#### `obd cluster destroy`

销毁已部署的集群。如果集群处于运行中的状态，该命令会先尝试执行`stop`，成功后再执行`destroy`。

```shell
obd cluster destroy <deploy name> [-f]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项 `-f` 为 `--force-kill`。检查到工作目录下有运行中的进程时，强制停止。销毁前会做检查是有还有进程在运行中。这些运行中的进程可能是 **start** 失败留下的，也可能是因为配置与其他集群重叠，进程是其他集群的。但无论是哪个原因导致工作目录下有进程未退出，**destroy** 都会直接停止。使用该选项会强制停止这些运行中的进程，强制执行 **destroy**。非必填项。数据类型为 `bool`。默认不开启。

### 测试命令组

#### `obd test mysqltest`

对 OcecanBase 数据库或 ODP 组件的指定节点执行 mysqltest。mysqltest 需要 OBClient，请先安装 OBClient。

```shell
obd test mysqltest <deploy name> [--test-set <test-set>] [flags]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- | ---
-c/--component | 否 | string | 默认为空 | 待测试的组件名。候选项为 oceanbase-ce 和 obproxy。为空时，按 obproxy、oceanbase-ce 的顺序进行检查。检查到组件存在则不再遍历，使用命中的组件进行后续测试。
--test-server | 否 | string | 默指定的组件下服务器中的第一个节点。 | 必须是指定的组件下的某个节点名。
--user | 否 | string | root | 执行测试的用户名。
---password | 否 | string | 默认为空 | 执行测试的用户密码。
--mysqltest-bin | 否 | string | mysqltest | 指定的路径不可执行时使用 OBD 自带的 mysqltest。
--obclient-bin | 否 | string | obclient | OBClient 二进制文件所在目录。
--test-dir | 否 | string | ./mysql_test/t | mysqltest 所需的 **test-file** 存放的目录。test 文件找不到时会尝试在 OBD 内置中查找。
--result-dir | 否 | string | ./mysql_test/r | mysqltest 所需的 **result-file** 存放的目录。result 文件找不到时会尝试在 OBD 内置中查找。
--tmp-dir | 否 | string | ./tmp | 为 mysqltest tmpdir 选项。
--var-dir | 否 | string | ./var | 将在该目录下创建log目录并作为 logdir 选项传入 mysqltest。
--test-set | 否 | string | 无 | test case 数组。多个数组使用英文逗号（,）间隔。
--test-pattern | 否 | string | 无| test 文件名匹配的正则表达式。所有匹配表达式的case将覆盖test-set选项。
--suite | 否 | string | 无 | suite 数组。一个 suite 下包含多个 test。可以使用英文逗号（,）间隔。使用该选项后 --test-pattern 和 --test-set 都将失效。
--suite-dir | 否 | string | ./mysql_test/test_suite | 存放 suite 目录的目录。suite 目录找不到时会尝试在 OBD 内置中查找。
--all | 否 | bool | false | 执行 --suite-dir 下全部的 case。存放 suite 目录的目录。
--need-init | 否 | bool |  false | 执行init sql 文件。一个新的集群要执行 mysqltest 前可能需要执行一些初始化文件，比如创建 case 所需要的账号和租户等。存放 suite 目录的目录。默认不开启。
--init-sql-dir | 否 | string | ../ | init sql 文件所在目录。sql 文件找不到时会尝试在obd内置中查找。
--init-sql-files | 否 | string | | 需要 init 时执行的 init sql 文件数组。英文逗号（,）间隔。不填时，如果需要 init，OBD 会根据集群配置执行内置的 init。
--auto-retry | 否 | bool | false | 失败时自动重部署集群进行重试。

## Q&A

### Q: 如何指定使用组件的版本？

A: 在部署配置文件中使用版本声明。例如，如果您使用的是 OceanBase-CE 3.1.0 版本，可以指定以下配置：

```yaml
oceanbase-ce:
  version: 3.1.0
```

### Q: 如何指定使用特定版本的组件？

A: 在部署配置文件中使用 package_hash 或 tag 声明。
如果您给自己编译的 OceanBase-CE 设置了t ag，您可以使用 tag 来指定。如：

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

A：您可以修改 `~/.obd/plugins/oceanbase-ce/` 下的启动相关插件。比如您为 3.1.0 版本的 OceanBase-CE 添加了一个新的启动配置，可以修改 ``~/.obd/plugins/oceanbase-ce/3.1.0/start.py``。

## 协议

OBD 采用 [GPL-3.0](./LICENSE) 协议。
