# OceanBase Deployer

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

OceanBase Deployer (OBD) is an installation and deployment tool for open-source OceanBase software. It is also a package manager for managing all open-source OceanBase software. This topic describes how to install OBD, how to use OBD, and OBD commands.

## Install OBD

You can install OBD by using these methods:

### Method 1: Install OBD by using RPM packages (only for CentOS 7 or later)

```shell
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://mirrors.aliyun.com/oceanbase/OceanBase.repo
sudo yum install -y ob-deploy
source /etc/profile.d/obd.sh
```

### Method 2: Install OBD by using the source code

Before you install OBD by using the source code, make sure that you have installed these dependencies:

- gcc
- wget
- python-devel
- openssl-devel
- xz-devel
- mysql-devel

To install OBD on Python2.7, run these commands:

```shell
pip install -r requirements.txt
sh build.sh
source /etc/profile.d/obd.sh
```

To install OBD on Python3.8, run these commands:

```shell
pip install -r requirements3.txt
sh build.sh
source /etc/profile.d/obd.sh
```

## Start an OceanBase cluster

After you install OBD, you can run these commands as the root user to start a local single-node OceanBase cluster.
Before you run the commands, make sure that these conditions are met:

- You have logged on as the root user.
- Ports `2882` and `2883` are available.
- Your server has at least 8 GB of memory.
- Your server has at least 2 CPU cores.

> **NOTE:** If the preceding conditions are not met, see [Use OBD to start an OceanBase cluster](./docs/docs-en/install-and-use/start-OceanBase-cluster-with-obd.md).

> **NOTE:** For the convenience of using root here, OBD and OceanBase database do not have any restrictions on running users. We do not recommend that you use root in production.

```shell
obd cluster deploy c1 -c ./example/mini-local-example.yaml
obd cluster start c1
# Connect to the OceanBase Database by using a MySQL client.
mysql -h127.1 -uroot -P2883
```

## Use OBD to start an OceanBase cluster

If you want to know how to use OBD to start an OceanBase cluster, please see [Use OBD to start an OceanBase cluster](./docs/docs-en/install-and-use/start-OceanBase-cluster-with-obd.md).

## Other OBD commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

- [Mirror and repository commands](./docs/docs-en/obd-commands/mirror-and-repository-commands.md)
- [Cluster commands](./docs/docs-en/obd-commands/cluster-commands.md)
- [Testing commands](./docs/docs-en/obd-commands/testing-commands.md)

## Q&A

### Q: How can I specify the version of a component?

A: You can add the version declaration to the deployment configuration file. For example, you can specify the version of OceanBase-CE V3.1.0 in the deployment configuration file in the following format:

```yaml
oceanbase-ce:
  version: 3.1.0
```

### Q: How can I use a component of a specific version?

A: You can add the package_hash or tag declaration to the deployment configuration file.
For example, if you have tagged your compiled OceanBase-CE, you can specify it by tag. For example:

```yaml
oceanbase-ce:
  tag: my-oceanbase
```

You can also use package_hash to specify a specific version. When you run an `obd mirror` command, OBD will return an MD5 value of the component. The MD5 value is the value of package_hash.

```yaml
oceanbase-ce:
  package_hash: 929df53459404d9b0c1f945e7e23ea4b89972069
```

### Q: How can I modify the startup process after I modify the code of OceanBase-CE?

A: You can modify the startup plug-ins in the `~/.obd/plugins/oceanbase-ce/` directory. For example, after you add a new startup configuration item for OceanBase-CE V3.1.0, you can modify the `start.py` file in the `~/.obd/plugins/oceanbase-ce/3.1.0` directory.

### Q：How to update OBD?

A：You can use the `obd update` command to update OBD. When you are done with the update, use `obd --version` to confirm you version.

## Protocol

OBD complies with [GPL-3.0](/LICENSE).
