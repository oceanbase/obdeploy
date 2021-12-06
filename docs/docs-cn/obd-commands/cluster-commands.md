# 集群命令组

OBD 有多级命令，您可以在每个层级中使用 `-h/--help` 选项查看子命令的帮助信息。

OBD 集群命令操作的最小单位为一个部署配置。部署配置是一份 `yaml` 文件，里面包含各个整个部署的全部配置信息，包括服务器登录信息、组件信息、组件配置信息和组件服务器列表等。

在使用 OBD 启动一个集群之前，您需要先注册这个集群的部署配置到 OBD 中。您可以使用 `obd cluster edit-config` 创建一个空的部署配置，或使用 `obd cluster deploy -c config` 导入一个部署配置。

## `obd cluster autodeploy`

传入一个简易的配置文件，OBD 会根据目标机器资源自动生成最大规格的完整配置并部署启动集群。

```shell
obd cluster autodeploy <deploy name> -c <yaml path> [-f] [-U] [-A] [-s]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- |---
-c/--config | 是 | string | 无 | 使用指定的 yaml 文件部署，并将部署配置注册到 OBD 中。<br>当`deploy name` 存在时，会判断其状态，如果旧配置尚未部署则覆盖，否则报错。
-f/--force | 否 | bool | false | 开启时，强制清空工作目录。<br>当组件要求工作目录为空且不使用该选项时，工作目录不为空会返回错误。
-U/--ulp/ --unuselibrepo | 否 | bool | false | 使用该选项将禁止 OBD 自动处理依赖。不开启的情况下，OBD 将在检查到缺失依赖时搜索相关的 libs 镜像并安装。使用该选项将会在对应的配置文件中添加 **unuse_lib_repository: true**。也可以在配置文件中使用 **unuse_lib_repository: true** 开启。
-A/--act/--auto-create-tenant | 否 | bool | false | 开启该选项 OBD 将会在 bootstrap 阶段使用集群全部可用资源创建一个名为 `test` 的租户。使用该选项将会在对应的配置文件中添加 **auto_create_tenant: true**。也可以在配置文件中使用 **auto_create_tenant: true** 开启。
-s/--strict-check | 否 | bool | false | 部分组件在启动前会做相关的检查，当检查不通过的时候会报警告，不会强制停止流程。使用该选项可开启检查失败报错直接退出。建议开启，可以避免一些资源不足导致的启动失败。

## `obd cluster edit-config`

修改一个部署配置，当部署配置不存在时创建。

```shell
obd cluster edit-config <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

## `obd cluster deploy`

根据配置部署集群。此命令会根据部署配置文件中组件的信息查找合适的镜像，并安装到本地仓库，此过程称为本地安装。
再将本地仓库中存在合适版本的组件分发给目标服务器，此过程称为远程安装。
在本地安装和远程安装时都会检查服务器是否存在组件运行所需的依赖。
此命令可以直接使用 OBD 中已注册的 `deploy name` 部署，也可以通过传入 `yaml` 的配置信息。

```shell
obd cluster deploy <deploy name> [-c <yaml path>] [-f] [-U] [-A]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- |---
-c/--config | 否 | string | 无 | 使用指定的 yaml 文件部署，并将部署配置注册到 OBD 中。<br>当 `deploy name` 存在时覆盖配置。<br>如果不使用该选项，则会根据 `deploy name` 查找已注册到 OBD 中的配置信息。
-f/--force | 否 | bool | false | 开启时，强制清空工作目录。<br>当组件要求工作目录为空且不使用改选项时，工作目录不为空会返回错误。
-U/--ulp/ --unuselibrepo | 否 | bool | false | 使用该选项将禁止 OBD 自动处理依赖。不开启的情况下，OBD 将在检查到缺失依赖时搜索相关的 libs 镜像并安装。使用该选项将会在对应的配置文件中添加 **unuse_lib_repository: true**。也可以在配置文件中使用 **unuse_lib_repository: true** 开启。
-A/--act/--auto-create-tenant | 否 | bool | false | 开启该选项 OBD 将会在 bootstrap 阶段使用集群全部可用资源创建一个名为 `test` 的租户。使用该选项将会在对应的配置文件中添加 **auto_create_tenant: true**。也可以在配置文件中使用 **auto_create_tenant: true** 开启。
<!-- --force-delete | 否 | bool | false | 强制删除，删除已注册的集群。
-s/--strict-check | 否 | bool | false | 当检查失败时抛出错误而不是警告。 -->

## `obd cluster start`

启动已部署的集群，成功时打印集群状态。

```shell
obd cluster start <deploy name> [flags]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- |---
-s/--servers | 否 | string | 空 | 机器列表，用 `,` 间隔。用于指定启动的机器。如果组件下的机器没有全部启动，则 start 不会执行 bootstrap。
-c/--components | 否 | string | 空 | 组件列表，用 `,` 间隔。用于指定启动的组件。如果配置下的组件没有全部启动，该配置不会进入 running 状态。
--wop/--without-parameter | 否 | bool | false | 无参启动。启动的时候不带参数。节点第一次的启动时，不响应此选项。
-S/--strict-check | 否 | bool | false | 部分组件在启动前会做相关的检查。检查不通过时，OBD 将发出告警，不会强制停止流程。使用该选项可开启检查失败报错直接退出。建议开启，可以避免一些资源不足导致的启动失败。

## `obd cluster list`

显示当前 OBD 内注册的全部集群（deploy name）的状态。

```shell
obd cluster list
```

## `obd cluster display`

展示指定集群的状态。

```shell
obd cluster display <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

## `obd cluster reload`

重载一个运行中集群。当您使用 `edit-config` 修改一个运行的集群的配置信息后，可以通过 `reload` 命令应用修改。

> **注意**：并非全部的配置项都可以通过 `reload` 来应用。有些配置项需要重启集群，甚至是重新部署集群才能生效。请根据 `edit-config` 后返回的信息进行操作。

```shell
obd cluster reload <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

## `obd cluster restart`

重启一个运行中集群。当您使用 edit-config 修改一个运行的集群的配置信息后，可以通过 `restart` 命令应用修改。

> **注意：** 并非所有的配置项都可以通过 `restart` 来应用。有些配置项需要重部署集群才能生效。请根据 `edit-config` 后返回的信息进行操作。

```shell
obd cluster restart <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- |---
-s/--servers | 否 | string | 空 | 机器列表，用 `,` 间隔。
-c/--components | 否 | string | 空 | 组件列表，用 `,` 间隔。用于指定启动的组件。如果配置下的组件没有全部启动，该配置不会进入 running 状态。
--wop/--without-parameter | 否 | bool | false | 无参启动。启动的时候不带参数。节点第一次的启动时，不响应此选项。

## `obd cluster redeploy`

重启一个运行中集群。当您使用 `edit-config` 修改一个运行的集群的配置信息后，可以通过 `redeploy` 命令应用修改。

> **注意：** 该命令会销毁集群，重新部署，您集群中的数据会丢失，请先做好备份。

```shell
obd cluster redeploy <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

## `obd cluster stop`

停止一个运行中的集群。

```shell
obd cluster stop <deploy name>
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- |---
-s/--servers | 否 | string | 空 | 机器列表，用 `,` 间隔。用于指定停止的机器。
-c/--components | 否 | string | 空 | 组件列表，用 `,` 间隔。用于指定停止的组件。如果配置下的组件没有全部停止，该配置不会进入 stopped 状态。

## `obd cluster destroy`

销毁已部署的集群。如果集群处于运行中的状态，该命令会先尝试执行 `stop`，成功后再执行 `destroy`。

```shell
obd cluster destroy <deploy name> [-f]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项 `-f` 为 `--force-kill`。检查到工作目录下有运行中的进程时，强制停止。销毁前会做检查是有还有进程在运行中。这些运行中的进程可能是 **start** 失败留下的，也可能是因为配置与其他集群重叠，进程是其他集群的。但无论是哪个原因导致工作目录下有进程未退出，**destroy** 都会直接停止。使用该选项会强制停止这些运行中的进程，强制执行 **destroy**。非必填项。数据类型为 `bool`。默认不开启。

## `obd cluster tenant create`

创建租户。该命令仅对 OceanBase 数据库有效。该命令会自动创建资源单元和资源池，用户不需要手动创建。

```shell
obd cluster tenant create <deploy name> [-n <tenant name>] [flags]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 默认值 | 说明
--- | --- | --- |--- | ---
-n/--tenant-name | 否 | string |  test | 租户名。对应的资源单元和资源池根据租户名自动生成，并且避免重名。
--max-cpu | 否 | float | 0 | 租户可用最大 CPU 数。为 0 时使用集群剩余全部可用 CPU。
--min-cpu | 否 | float | 0 | 租户可用最小 CPU 数。为 0 时等于 --max-cpu。
--max-memory | 否 | int | 0 | 租户可用最大内存。为 0 时使用集群剩余全部可用内存。实际值低于 1G 时报错。
--min-memory | 否 | int | 0 | 租户可用最小内存。为 0 时等于 --max-memory。
--max-disk-size | 否 | int | 0 | 租户可用最大磁盘空间。为0时使用集群全部可用空间。实际值低于 512M 时报错。
--max-iops | 否 | int | 128 | 租户 IOPS 最多数量，取值范围为 [128,+∞)。
--min-iops | 否 | int | 0 | 租户 IOPS 最少数量。取值范围为 [128,+∞)。为 0 时等于 --max-iops 。
--max-session-num | 否 | int | 64 | 租户 最大 SESSION 数，取值范围为 [64,+∞)。
--unit-num | 否 | int | 0 | 指定要创建的单个 ZONE 下的单元个数，取值要小于单个 ZONE 中的 OBServer 个数。为 0 自动获取最大值。
-z/--zone-list | 否 | string | 空 | 指定租户的 ZONE 列表，多个 ZONE 用英文逗号（,）间隔。为空时等于集群全部 ZONE。
--primary-zone | 否 | string | RANDOM | 租户的主 Zone。
--charset | 否 | string | 空 | 租户的字符集。
--collate | 否 | string | 空 | 租户校对规则。
--replica-num | 否 | int | 0 | 租户副本数。为 0 时等于 ZONE 的数目。
--logonly-replica-num | 否 | string | 0 | 租户日志副本数。为 0 时等于 --replica-num。
--tablegroup | 否 | string | 空 | 租户默认表组信息
--locality | 否 | string | 空 | 描述副本在 Zone 间的分布情况，如：F@z1,F@z2,F@z3,R@z4 表示 z1, z2, z3 为全功能副本，z4 为只读副本。
-s/--variables | 否 | string | ob_tcp_invited_nodes='%' | 设置租户系统变量值。

## `obd cluster tenant drop`

删除租户。该命令仅 OceanBase 数据库有效。该命令会自动删除对应的资源单元和资源池。

```shell
obd cluster tenant drop <deploy name> [-n <tenant name>]
```

参数 `deploy name` 为部署配置名称，可以理解为配置文件名称。

选项 `-n` 为 `--tenant-name`。要删除的租户名。必填项。
