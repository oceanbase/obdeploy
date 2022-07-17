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
