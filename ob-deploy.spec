Name: ob-deploy
Version: 1.0.1
Release: 1%{?dist}
# if you want use the parameter of rpm_create on build time,
# uncomment below
Summary: ob-deploy
Group: Development/Tools
License: GPL
Url: git@github.com:oceanbase/obdeploy.git
BuildRoot:  %_topdir/BUILDROOT
%define debug_package %{nil}
%define __os_install_post %{nil}


# uncomment below, if your building depend on other packages

# uncomment below, if depend on other packages

Autoreq: 0
# BuildRequires: mariadb-devel


%description
# if you want publish current svn URL or Revision use these macros
ob-deploy

%debug_package
# support debuginfo package, to reduce runtime package size

# prepare your files
# OLDPWD is the dir of rpm_create running
# _prefix is an inner var of rpmbuild,
# can set by rpm_create, default is "/home/a"
# _lib is an inner var, maybe "lib" or "lib64" depend on OS

# create dirs
%install
SRC_DIR=$OLDPWD
BUILD_DIR=$OLDPWD/rpmbuild
rm -fr cd $SRC_DIR/mirror/remote && mkdir -p $SRC_DIR/mirror/remote && cd $SRC_DIR/mirror/remote 
wget https://mirrors.aliyun.com/oceanbase/OceanBase.repo
cd $SRC_DIR/
rm -rf $BUILD_DIR build.log ${RPM_BUILD_ROOT} build dist obd.spec
CID=`git log |head -n1 | awk -F' ' '{print $2}'`
BRANCH=`git branch | grep -e "^\*" | awk -F' ' '{print $2}'`
DATE=`date '+%b %d %Y %H:%M:%S'`
cat _cmd.py | sed "s/<CID>/$CID/" | sed "s/<B_BRANCH>/$BRANCH/" | sed "s/<B_TIME>/$DATE/" > obd.py
mkdir -p $BUILD_DIR/SOURCES ${RPM_BUILD_ROOT}
mkdir -p $BUILD_DIR/SOURCES/{site-packages}
mkdir -p ${RPM_BUILD_ROOT}/usr/bin
mkdir -p ${RPM_BUILD_ROOT}/usr/obd
pip install -r plugins-requirements3.txt --target=$BUILD_DIR/SOURCES/site-packages
pyinstaller --hidden-import=decimal --hidden-import=configparser -F obd.py
rm -f obd.py obd.spec
\cp -rf $SRC_DIR/dist/obd ${RPM_BUILD_ROOT}/usr/bin/obd
\cp -rf $SRC_DIR/plugins $BUILD_DIR/SOURCES/plugins
\rm -fr $BUILD_DIR/SOURCES/plugins/oceanbase-ce
\cp -rf $SRC_DIR/profile/ $BUILD_DIR/SOURCES/
\cp -rf $SRC_DIR/mirror/ $BUILD_DIR/SOURCES/
\cp -rf $BUILD_DIR/SOURCES/plugins ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/mirror ${RPM_BUILD_ROOT}/usr/obd/
mkdir -p ${RPM_BUILD_ROOT}/etc/profile.d/
\cp -rf $BUILD_DIR/SOURCES/profile/* ${RPM_BUILD_ROOT}/etc/profile.d/
mkdir -p ${RPM_BUILD_ROOT}/usr/obd/lib/
\cp -rf $BUILD_DIR/SOURCES/site-packages ${RPM_BUILD_ROOT}/usr/obd/lib/site-packages
cd ${RPM_BUILD_ROOT}/usr/obd/plugins && ln -s oceanbase oceanbase-ce

# package infomation
%files
# set file attribute here
%defattr(-,root,root,0777)
# need not list every file here, keep it as this
/usr/bin/obd
/usr/obd/*
/etc/profile.d/*
## create an empy dir


## need bakup old config file, so indicate here


## or need keep old config file, so indicate with "noreplace"

## indicate the dir for crontab


%post
# chkconfig: 2345 10 90
# description: obd ....
chmod +x /usr/bin/obd
#mkdir -p /usr/obd/ && cp -rf /root/.obd/plugins /usr/obd/plugins
#chmod 744 /root/.obd/plugins/*
chmod -R 755 /usr/obd/*
chown -R root:root /usr/obd/*
find /usr/obd -type f -exec chmod 644 {} \;
echo -e 'Installation of obd finished successfully\nPlease source /etc/profile.d/obd.sh to enable it'
#/sbin/chkconfig --add obd
#/sbin/chkconfig obd on

%changelog
* Mon Jun 28 2021 obd 1.0.1
 - support configuration password
 - Multi-level checks before start
 - new features: obd cluster upgrade
 - new features: obd update
 - cancel the timeout limit for waiting for the cluster to initialize
 - new configuration item for store log
 - support SUSE, Ubuntu etc.