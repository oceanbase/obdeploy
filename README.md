# OceanBase Deployer

<!--
#
# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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

After you [deploy OceanBase Deployer (OBD)](./docs/en-US/200.quick-start/100.install-obd.md), you can run the `obd demo` command to deploy and start OceanBase Database on a single local server. Make sure the following prerequisites are met:

- Ports `2881` and `2882` are not occupied.

- At least 6 GB of memory is available on the server.

- At least two CPU cores are available on the server.

- At least 54 GB of disk space is available on the server.

```shell
# Deploy and start OceanBase Database.
obd demo
# Run the following command to connect to OceanBase Database by using the OBClient:
obclient -h127.0.0.1 -uroot -P2881
```

## Use OBD to start an OceanBase cluster

If you want to know how to use OBD to start an OceanBase cluster, please see [Use OBD to start an OceanBase cluster](./docs/en-US/400.user-guide/300.command-line-operations/200.start-the-oceanbase-cluster-by-using-obd.md).

## Other OBD commands

OBD provides multiple-level commands. You can use the`-h/--help` option to view the help information of sub-commands.

- [Mirror and repository commands](./docs/en-US/300.obd-command/200.command-group-for-mirroring-and-warehousing.md)
- [Cluster commands](./docs/en-US/300.obd-command/100.cluster-command-groups.md)
- [Testing commands](./docs/en-US/300.obd-command/300.test-command-group.md)

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

OBD complies with [Apache-2.0](/LICENSE).
