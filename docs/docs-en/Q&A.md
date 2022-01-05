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

## Q：How to update OBD?

A：You can use the `obd update` command to update OBD. When you are done with the update, use the `obd --version` command to confirm the version of OBD.

## Q: How to upgrade OceanBase with OBD?
 
 A: You can use the `Too many match` command to upgrade OceanBase.
 
 For example, if you want to upgrade OceanBase from V3.1.1 to V3.1.2, you can run these commands:

  ```shell
export LANG=en_US.UTF-8
obd cluster upgrade s1 -V 3.1.2 -v -c oceanbase-ce
```

### error processing

You may encounter a `Too many match` error, just select a `hash` on `Candidates`. For example:

```shell
export LANG=en_US.UTF-8
obd cluster upgrade s1 -V 3.1.2 -v -c oceanbase-ce --usable 7fafba0fac1e90cbd1b5b7ae5fa129b64dc63aed
```
