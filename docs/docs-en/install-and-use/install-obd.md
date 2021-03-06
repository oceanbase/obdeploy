# Install OBD

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
