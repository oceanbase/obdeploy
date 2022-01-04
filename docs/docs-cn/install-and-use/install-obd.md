# 安装 OBD

您可以使用以下方式安装 OBD：

## 方案1： 使用 RPM 包（Centos 7 及以上）安装

```shell
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://mirrors.aliyun.com/oceanbase/OceanBase.repo
sudo yum install -y ob-deploy
source /etc/profile.d/obd.sh
```

## 方案2：使用源码安装

使用源码安装 OBD 之前，请确认您已安装以下依赖：

- gcc
- wget
- python-devel
- openssl-devel
- xz-devel
- mysql-devel
  
Python2.7 使用以下命令安装：

```shell
pip install -r requirements.txt
sh build.sh
source /etc/profile.d/obd.sh
```

Python3.8 使用以下命令安装：

```shell
pip install -r requirements3.txt
sh build.sh
source /etc/profile.d/obd.sh
```

> **注意：** 为了与 release 版本区分开，源码安装产生的版本号为 4 位版本号，即在 rpm 包的版本号基础上加上安装时间，比如 1.2.0.1641267289。

另外您可通过在安装前设置环境变量 `export OBD_DUBUG=1` 安装开启 DEBUG 模式的 OBD，该模式下每一条命令结束后都会输出对应的 trace id 以方便问题定位。
