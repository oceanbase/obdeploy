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

## Q：如何升级 OBD？

A：您可以使用 `obd update` 命令升级 OBD。当您升级完成后可以使用命令 `obd --version` 查看版本，确认是否升级成功。

## Q：如何使用 OBD 升级 OceanBase 数据库？

A：您可使用 `obd cluster upgrade` 命令升级 OceanBase 数据库。

例如，若您想要从 OceanBase V3.1.1 升级到 V3.1.2，命令如下：

```shell
export LANG=en_US.UTF-8
obd cluster upgrade s1 -V 3.1.2 -v -c oceanbase-ce
```

### 报错处理

您可能会遇到 `Too many match` 的报错，这时只需在 `Candidates` 上选择一个 `hash` 即可。比如：

```shell
export LANG=en_US.UTF-8
obd cluster upgrade s1 -V 3.1.2 -v -c oceanbase-ce --usable 7fafba0fac1e90cbd1b5b7ae5fa129b64dc63aed
```
