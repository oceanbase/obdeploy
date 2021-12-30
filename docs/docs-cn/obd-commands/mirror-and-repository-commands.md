# 镜像和仓库命令组

OBD 有多级命令，您可以在每个层级中使用 `-h/--help` 选项查看子命令的帮助信息。

## `obd mirror clone`

将一个 RPM 包复制到本地镜像库，之后您可以使用 OBD 集群中相关的命令启动镜像。

```shell
obd mirror clone <path> [-f]
```

参数 `path` 为 RPM 包的路径。

选项 `-f` 为 `--force`。`-f` 为可选选项。默认不开启。开启时，当镜像已经存在时，强制覆盖已有镜像。

## `obd mirror create`

以本地目录为基础创建一个镜像。此命令主要用于使用 OBD 启动自行编译的 OceanBase 开源软件，您可以通过此命令将编译产物加入本地仓库，之后就可以使用 `obd cluster` 相关的命令启动这个镜像。

```shell
obd mirror create -n <component name> -p <your compile dir> -V <component version> [-t <tag>] [-f]
```

例如，如果您根据 [OceanBase 数据库编译指导书](https://open.oceanbase.com/docs/community/oceanbase-database/V3.1.0/get-the-oceanbase-database-by-using-source-code)编译 OceanBase 数据库，在编译成功后，可以使用 `make DESTDIR=./ install && obd mirror create -n oceanbase-ce -V 3.1.0 -p ./usr/local` 命令将编译产物添加至 OBD 本地仓库。

选项说明见下表：

选项名 | 是否必选 | 数据类型 | 说明
--- | --- | --- |---
-n/--name | 是 | string | 组件名。如果您编译的是 OceanBase 数据库，则填写 oceanbase-ce。如果您编译的是 ODP，则填写 obproxy。
-p/--path | 是 | string | 编译目录。执行编译命令时的目录。OBD 会根据组件自动从该目录下获取所需的文件。
-V/--version | 是 | string | 版本号。
-t/--tag | 否 | string | 镜像标签。您可以为您的创建的镜像定义多个标签，以英文逗号（,）间隔。
-f/--force | 否 | bool | 当镜像已存在，或者标签已存在时强制覆盖。默认不开启。

## `obd mirror list`

显示镜像仓库或镜像列表。

```shell
obd mirror list [mirror repo name]
```

参数 `mirror repo name` 为镜像仓库名。该参数为可选参数。为空时，将显示镜像仓库列表。不为空时，则显示对应仓库的镜像列表。

## `obd mirror update`

同步全部远程镜像仓库的信息。

```shell
obd mirror update
```

## `obd mirror disable`

禁用远程镜像仓库。如果需要禁用所有远程镜像仓库，执行 `obd mirror disable remote` 命令。

```shell
obd mirror disable <mirror_repo_name>
```

参数 `mirror repo name` 为镜像仓库名。如果指定 `remote`，则会禁用所有远程镜像仓库。

## `obd mirror enable`

启用远程镜像仓库。

```shell
obd mirror enable <mirror repo name>
```

参数 `mirror repo name` 为镜像仓库名。如果指定 `remote`，则会启用所有远程镜像仓库。
