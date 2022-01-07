# Q&A

## Q: How can I specify the version of a component?

A: You can add the version declaration to the deployment configuration file. For example, you can specify the version of OceanBase-CE V3.1.0 in the deployment configuration file in the following format:

```yaml
oceanbase-ce:
  version: 3.1.0
```

## Q: How can I use a component of a specific version?

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

## Q: How can I modify the startup process after I modify the code of OceanBase-CE?

A: You can modify the startup plug-ins in the `~/.obd/plugins/oceanbase-ce/` directory. For example, after you add a new startup configuration item for OceanBase-CE V3.1.0, you can modify the `start.py` file in the `~/.obd/plugins/oceanbase-ce/3.1.0` directory.

## Q: How to update OBD local mirror in offline mode?

A: When your machine with OBD installed cannot connect to the public network, but you need to update OBD or other components, you can download the RPM package you need on another machine that can connect to the public network, copy the RPM package to the machine where OBD installed, and then add the new RPM package to the local mirror through `obd mirror clone` command.

The following shows how to update the OBD mirror in the local repository:
```shell
# First, download the OBD 1.2.1 el7 RPM package on a machine that can connect to the public network.
# Links to the latest RPM packages are available in the release notes of the corresponding component's git repository or on the OceanBase open source website (https://open.oceanbase.com/softwareCenter/community).
wget https://github.com/oceanbase/obdeploy/releases/download/v1.2.1/ob-deploy-1.2.1-9.el7.x86_64.rpm
# Copy the downloaded RPM package to the machine where OBD is installed, i.e. obd_server.
sh ob-deploy-1.2.1-9.el7.x86_64.rpm obd_server:~
# Add the downloaded mirror to local.
obd mirror clone ob-deploy-1.2.1-9.el7.x86_64.rpm
# Close the remote mirror source.
obd mirror disable remote
```

## Q：How to update OBD?

A：There are two ways to update your OBD, which you can choose from depending on your situation:
+ If your machine can connect to the public network or have the RPM package for the updated OBD in the mirror you configured, you can directly use the `obd update` command to update the OBD. When you finish with the update, use the `obd --version` command to check the version of OBD and confirm whether the update is successful.
+ If your machine cannot connect to the public network and there is no RPM package for the updated OBD in the mirror you configured. Please add the RPM package that used to update OBD to the local mirror via `obd mirror clone` command first, and then use the `obd update` command to update the OBD.

The following shows how to update OBD to V1.2.1 on CentOS7 offline mode:
```shell
# First, download the OBD 1.2.1 el7 RPM package on a machine that can connect to the public network.
#  Links to the latest RPM packages are available in the release notes of the corresponding component's git repository or on the OceanBase open source website (https://open.oceanbase.com/softwareCenter/community).
wget https://github.com/oceanbase/obdeploy/releases/download/v1.2.1/ob-deploy-1.2.1-9.el7.x86_64.rpm
# Copy the downloaded RPM package to the machine where OBD is installed, i.e. obd_server.
sh ob-deploy-1.2.1-9.el7.x86_64.rpm obd_server:~
# Execute the following command on the OBD machine to complete the upgrade.
# 1.Add the downloaded mirror to local.
obd mirror clone ob-deploy-1.2.1-9.el7.x86_64.rpm
# 2.Close the remote mirror source.
obd mirror disable remote
# 3.Update.
obd update
```

## Q: How to upgrade OceanBase with OBD?
 
A: There are two ways to upgrade OceanBase with OBD, which you can choose from depending on your situation:
+ If your machine can connect to the public network or have the RPM package for the updated OceanBase in the mirror you configured, you can directly use the `obd cluster upgrade` command to upgrade the OceanBase.
+ If your machine cannot connect to the public network and there is no RPM package for the updated OceanBase in the mirror you configured. Please add the RPM package that used to update OceanBase to the local mirror via `obd mirror clone` command first, and then use the `obd cluster upgrade` command to upgrade the OceanBase.

The following shows how to upgrade OceanBase-CE from V3.1.1 to V3.1.2 with OBD on CentOS7 offline mode:

```shell
# First, you should check your OBD version, and if the version is lower than V1.2.1, please update the OBD version.
# Download the OceanBase-CE RPM package on a machine that can connect to the public network.
# Links to the latest RPM packages are available in the release notes of the corresponding component's git repository or on the OceanBase open source website (https://open.oceanbase.com/softwareCenter/community).
wget https://github.com/oceanbase/oceanbase/releases/download/v3.1.2_CE/oceanbase-ce-3.1.2-10000392021123010.el7.x86_64.rpm
# Copy the downloaded RPM package to the machine where OBD is installed, i.e. obd_server.
sh oceanbase-ce-3.1.2-10000392021123010.el7.x86_64.rpm obd_server:~
# Execute the following command on the OBD machine to complete the upgrade.
# 1.Add the downloaded mirror to local.
obd mirror clone oceanbase-ce-3.1.2-10000392021123010.el7.x86_64.rpm
# 2.Close the remote mirror source.
obd mirror disable remote
# 3.Upgrade.
obd cluster upgrade <deploy name> -c oceanbase-ce -V 3.1.2
```

### error processing

You may encounter a `Too many match` error, just select a `hash` on `Candidates`. For example:

```shell
obd cluster upgrade <deploy name> -c oceanbase-ce -V 3.1.2 --usable 7fafba0fac1e90cbd1b5b7ae5fa129b64dc63aed
```
