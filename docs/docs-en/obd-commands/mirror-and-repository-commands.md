# Mirror and repository commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

## `obd mirror clone`

Copy an RPM package to the local mirror repository. You can run the corresponding OBD cluster command to start the mirror.

```shell
obd mirror clone <path> [-f]
```

`path` specifies the path of the RPM package.

The `-f` option is `--force`. `-f` is optional. This option is disabled by default. If it is enabled and a mirror of the same name exists in the repository, the copied mirror will forcibly overwrite the existing one.

## `obd mirror create`

Creates a mirror based on the local directory. When OBD starts a user-compiled open-source OceanBase software, you can run this command to add the compilation output to the local repository. Then, you can run the corresponding `obd cluster` command to start the mirror.

```shell
obd mirror create -n <component name> -p <your compile dir> -V <component version> [-t <tag>] [-f]
```

For example, you can [compile an OceanBase cluster based on the source code](https://open.oceanbase.com/docs/community/oceanbase-database/V3.1.1/get-the-oceanbase-database-by-using-source-code). Then, you can run the `make DESTDIR=./ install && obd mirror create -n oceanbase-ce -V 3.1.0 -p ./usr/local` command to add the compilation output to the local repository of OBD.

This table describes the corresponding options.

| Option | Required | Data type | Description |
--- | --- | --- |---
| -n/--name | Yes | string | The component name. If you want to compile an OceanBase cluster, set this option to oceanbase-ce. If you want to compile ODP, set this option to obproxy.  |
| -p/--path | Yes | string | The directory that stores the compilation output. OBD will automatically retrieve files required by the component from this directory.  |
| -V/--version | Yes | string | The component version.  |
| -t/--tag | No | string | The mirror tags. You can define one or more tags for the created mirror. Separate multiple tags with commas (,).  |
| -f/--force | No | bool | Specifies whether to forcibly overwrite an existing mirror or tag. This option is disabled by default.  |

## `obd mirror list`

Shows the mirror repository or mirror list.

```shell
obd mirror list [mirror repo name]
```

`mirror repo name` specifies the mirror repository name. This parameter is optional. When it is not specified, all mirror repositories will be returned. When it is specified, only the specified mirror repository will be returned.

## `obd mirror update`

Synchronizes the information of all remote mirror repositories.

```shell
obd mirror update
```
