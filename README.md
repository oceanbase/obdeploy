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

To install OBD on Python3.8, run these commands:

```shell
pip install -r requirements3.txt
sh build.sh build_obd
source /etc/profile.d/obd.sh
```

## Start an OceanBase cluster

After you deploy OceanBase Deployer (OBD), you can run the `obd demo` command to deploy and start OceanBase Database on a single local server. Make sure the following prerequisites are met:

- Ports `2881` and `2882` are not occupied.

- At least 6 GB of memory is available on the server.

- At least two CPU cores are available on the server.

- At least 54 GB of disk space is available on the server.

> **Note**
>
> If the foregoing prerequisites are not met, see [Use OBD to start an OceanBase cluster](../3.user-guide/2.start-the-oceanbase-cluster-by-using-obd.md).

```shell
# Deploy and start OceanBase Database.
obd demo
# Run the following command to connect to OceanBase Database by using the OBClient:
obclient -h127.0.0.1 -uroot -P2881
```

## Use OBD to start an OceanBase cluster

If you want to know how to use OBD to start an OceanBase cluster, please see [Use OBD to start an OceanBase cluster](./docs/en-US/3.user-guide/2.start-the-oceanbase-cluster-by-using-obd.md).

## Other OBD commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

- [Mirror and repository commands](./docs/en-US/3.user-guide/3.obd-command/2.command-group-for-mirroring-and-warehousing.md)
- [Cluster commands](./docs/en-US/3.user-guide/3.obd-command/1.cluster-command-groups.md)
- [Testing commands](./docs/en-US/3.user-guide/3.obd-command/3.test-command-group.md)

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

A：You can use the `obd update` command to update OBD. When you are done with the update, use the `obd --version` command to confirm the version of OBD.

## Protocol

OBD complies with [GPL-3.0](/LICENSE).

## Sysbench benchmark

- [Run the Sysbench benchmark test in OceanBase Database (Paetica, VLDB 2023)](https://github.com/oceanbase/oceanbase-doc/blob/V4.1.0/en-US/7.reference/3.performance-tuning-guide/6.performance-whitepaper/3.run-the-sysbench-benchmark-test-in-oceanbase-database.md)
