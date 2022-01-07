# Q&A

## Q: 如何指定使用组件的版本？

A: 在部署配置文件中使用版本声明。例如，如果您使用的是 OceanBase-CE 3.1.0 版本，可以指定以下配置：

```yaml
oceanbase-ce:
  version: 3.1.0
```

## Q: 如何指定使用特定版本的组件？

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

## Q：我修改了 OceanBase-CE 了代码，需要修改启动流程怎么办？

A：您可以修改 `~/.obd/plugins/oceanbase-ce/` 下的启动相关插件。比如您为 3.1.0 版本的 OceanBase-CE 添加了一个新的启动配置，可以修改 `~/.obd/plugins/oceanbase-ce/3.1.0/start.py`。

## Q：如何在离线模式下更新 OBD 本地镜像？

A：当您安装 OBD 的机器不能连通公网，却需要更新 OBD 或其他组件时，您可先在一台可以连通公网的机器上下载好您需要的 RPM 包，将其拷贝到安装 OBD 的机器上后通过 `obd mirror clone` 将新的 RPM 包添加到 local mirror 中。

下面展示如何更新本地仓库中的 OBD 镜像：
```shell
# 先在一台可以连通公网的机器上下载 OBD 1.2.1 el7 RPM 包
# 最新的 RPM 包链接可以在对应的组件的 git 仓库中的 release note 或 OceanBase 开源官网（https://open.oceanbase.com/softwareCenter/community）中获得
wget https://github.com/oceanbase/obdeploy/releases/download/v1.2.1/ob-deploy-1.2.1-9.el7.x86_64.rpm
# 将下载好的 RPM 包拷贝到安装 OBD 的机器（obd_server）中
sh ob-deploy-1.2.1-9.el7.x86_64.rpm obd_server:~
# 将下载好的镜像加入到 local 中
obd mirror clone ob-deploy-1.2.1-9.el7.x86_64.rpm
# 关闭远程镜像源
obd mirror disable remote
```

## Q：如何升级 OBD？

A：升级 OBD 有以下两种方式，您可根据您的实际情况进行选择：
+ 如果您的机器可以连通公网或者您配置的 mirror 中有用于更新的 OBD 的 RPM 包，您可直接使用 `obd update` 命令升级 OBD。当您升级完成后可以使用命令 `obd --version` 查看版本，确认是否升级成功。
+ 如果您的机器不能连通公网且您配置的 mirror 中没有用于更新的 OBD 的 RPM 包，请先通过 `obd mirror clone` 将用于更新的 OBD 的 RPM 包添加到 local mirror 中，之后再使用 `obd update` 命令升级 OBD。

下面展示在离线模式下，如何在 CentOS7 系统中将 OBD 升级到 V1.2.1：
```shell
# 先在一台可以连通公网的机器上下载 OBD 1.2.1 el7 RPM 包
# 最新的 RPM 包链接可以在 git 仓库中的 release note 或 OceanBase 开源官网（https://open.oceanbase.com/softwareCenter/community）中获得
wget https://github.com/oceanbase/obdeploy/releases/download/v1.2.1/ob-deploy-1.2.1-9.el7.x86_64.rpm
# 将下载好的 RPM 包拷贝到安装 OBD 的机器（obd_server）中
sh ob-deploy-1.2.1-9.el7.x86_64.rpm obd_server:~
# 在 OBD 机器上执行以下命令完成升级
# 1.将下载好的镜像加入到 local 中
obd mirror clone ob-deploy-1.2.1-9.el7.x86_64.rpm
# 2.关闭远程镜像源
obd mirror disable remote
# 3.升级
obd update
```

## Q：如何使用 OBD 升级 OceanBase 数据库？

A：使用 OBD 升级 OceanBase 数据库有以下两种方式，您可根据您的实际情况进行选择：
+ 如果您的机器可以连通公网或者您配置的 mirror 中有用于更新的 OceanBase 数据库的 RPM 包，您可直接使用 `obd cluster upgrade` 命令升级 OceanBase 数据库。
+ 如果您的机器不能连通公网且您配置的 mirror 中没有用于更新的 OceanBase 数据库的 RPM 包，请先通过 `obd mirror clone` 将用于更新的 OceanBase 数据库的 RPM 包添加到 local mirror 中，之后再使用 `obd cluster upgrade` 命令升级 OceanBase 数据库。

下面展示在离线模式下，如何在 CentOS7 系统中使用 OBD 将 OceanBase-CE V3.1.1 升级到 V3.1.2：

```shell
# 请先确认您的 OBD 版本，如果版本低于 V1.2.1，请先更新 OBD 的版本
# 在一台可以连通公网的机器上下载 OceanBase-CE RPM 包
# 最新的 RPM 包链接可以在 git 仓库中的 release note 或 OceanBase 开源官网（https://open.oceanbase.com/softwareCenter/community）中获得
wget https://github.com/oceanbase/oceanbase/releases/download/v3.1.2_CE/oceanbase-ce-3.1.2-10000392021123010.el7.x86_64.rpm
# 将下载好的 RPM 包拷贝到安装 OBD 的机器（obd_server）中
sh oceanbase-ce-3.1.2-10000392021123010.el7.x86_64.rpm obd_server:~
# 在 OBD 机器上执行以下命令完成升级
# 1.将下载好的镜像加入到 local 中
obd mirror clone oceanbase-ce-3.1.2-10000392021123010.el7.x86_64.rpm
# 2.关闭远程镜像源
obd mirror disable remote
# 3.升级
obd cluster upgrade <deploy name> -c oceanbase-ce -V 3.1.2
```

### 报错处理

您可能会遇到 `Too many match` 的报错，这时只需在 `Candidates` 上选择一个 `hash` 即可。比如：

```shell
obd cluster upgrade <deploy name> -c oceanbase-ce -V 3.1.2 --usable 7fafba0fac1e90cbd1b5b7ae5fa129b64dc63aed
```
