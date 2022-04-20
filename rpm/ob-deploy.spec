Name: ob-deploy
Version: %(echo $VERSION)
Release: %(echo $RELEASE)%{?dist}
# if you want use the parameter of rpm_create on build time,
# uncomment below
Summary: ob-deploy
Group: Development/Tools
License: GPL
Url: git@github.com:oceanbase/obdeploy.git
# BuildRoot:  %_topdir/BUILDROOT
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
RPM_DIR=$OLDPWD
SRC_DIR=$OLDPWD/..
BUILD_DIR=$OLDPWD/rpmbuild
rm -fr $SRC_DIR/mirror/remote && mkdir -p $SRC_DIR/mirror/remote && cd $SRC_DIR/mirror/remote 
wget https://mirrors.aliyun.com/oceanbase/OceanBase.repo
cd $SRC_DIR/
rm -rf build.log build dist obd.spec
if [ `git log |head -n1 | awk -F' ' '{print $2}'` ]; then
    CID=`git log |head -n1 | awk -F' ' '{print $2}'`
    BRANCH=`git rev-parse --abbrev-ref HEAD`
else
    CID='UNKNOWN'
    BRANCH='UNKNOWN'
fi
DATE=`date '+%b %d %Y %H:%M:%S'`
VERSION="$RPM_PACKAGE_VERSION"
if  [ "$OBD_DUBUG" ]; then
    VERSION=$VERSION".`date +%s`"
fi
cat _cmd.py | sed "s/<CID>/$CID/" | sed "s/<B_BRANCH>/$BRANCH/" | sed "s/<B_TIME>/$DATE/" | sed "s/<DEBUG>/$OBD_DUBUG/" | sed "s/<VERSION>/$VERSION/" > obd.py
mkdir -p $BUILD_DIR/SOURCES ${RPM_BUILD_ROOT}
mkdir -p $BUILD_DIR/SOURCES/{site-packages}
mkdir -p ${RPM_BUILD_ROOT}/usr/bin
mkdir -p ${RPM_BUILD_ROOT}/usr/obd
pip install -r plugins-requirements3.txt --target=$BUILD_DIR/SOURCES/site-packages
pyinstaller --hidden-import=decimal --hidden-import=configparser -F obd.py
rm -f obd.py obd.spec
\cp -rf $SRC_DIR/dist/obd ${RPM_BUILD_ROOT}/usr/bin/obd
\cp -rf $SRC_DIR/plugins $BUILD_DIR/SOURCES/plugins
\cp -rf $SRC_DIR/config_parser $BUILD_DIR/SOURCES/config_parser
\rm -fr $BUILD_DIR/SOURCES/plugins/oceanbase-ce
\rm -fr $BUILD_DIR/SOURCES/plugins/obproxy-ce
\rm -fr $BUILD_DIR/SOURCES/config_parser/oceanbase-ce
\cp -rf $SRC_DIR/profile/ $BUILD_DIR/SOURCES/
\cp -rf $SRC_DIR/mirror/ $BUILD_DIR/SOURCES/
\cp -rf $BUILD_DIR/SOURCES/plugins ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/config_parser ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/mirror ${RPM_BUILD_ROOT}/usr/obd/
mkdir -p ${RPM_BUILD_ROOT}/etc/profile.d/
\cp -rf $BUILD_DIR/SOURCES/profile/* ${RPM_BUILD_ROOT}/etc/profile.d/
mkdir -p ${RPM_BUILD_ROOT}/usr/obd/lib/
\cp -rf $BUILD_DIR/SOURCES/site-packages ${RPM_BUILD_ROOT}/usr/obd/lib/site-packages
mkdir -p ${RPM_BUILD_ROOT}/usr/obd/lib/executer
\cp -rf ${RPM_DIR}/executer27 ${RPM_BUILD_ROOT}/usr/obd/lib/executer/
cd ${RPM_BUILD_ROOT}/usr/obd/plugins && ln -s oceanbase oceanbase-ce && mv obproxy obproxy-ce
cd ${RPM_BUILD_ROOT}/usr/obd/config_parser && ln -s oceanbase oceanbase-ce 

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
chmod -R 755 /usr/obd/*
chown -R root:root /usr/obd/*
find /usr/obd -type f -exec chmod 644 {} \;
chmod +x /usr/bin/obd
chmod +x /usr/obd/lib/executer/executer27/bin/executer
echo -e 'Installation of obd finished successfully\nPlease source /etc/profile.d/obd.sh to enable it'
#/sbin/chkconfig --add obd
#/sbin/chkconfig obd on

%changelog
* Wed Apr 20 2022 obd 1.3.2
 - fix bug: remote install will return None when success
* Wed Apr 20 2022 obd 1.3.1
 - new features: some alarm levels will be reduced when developer mode is turned on
 - fix bug: fail to connect obproxy when upgrade
 - fix bug: change ilog/clog/slog owner when user change
 - fix bug: typo: formate
* Wed Mar 30 2022 obd 1.3.0
 - new features: support rotation restart
 - new features: support switching deployment users
 - new features: obd cluster chst
 - new features: obd cluster check4ocp
 - fix bug: fixed the default path in tpch
 - fix bug: fixed the default component in sysbench
* Wed Jan 05 2022 obd 1.2.1
- fix bug: fixed the upgrade path encoding error when you use the obd cluster upgrade command without setting the Chinese environment.
- fix bug: fixed the problem caused by no mysqlt.connector dependency when you use the obd cluster upgrade command.
- fix bug: fixed OBD cannot choose and upgrade the target component when you have only one component.
* Fri Dec 31 2021 obd 1.2.0
 - new features: obd mirror disable/enable
 - new features: support obagent 1.1.0
 - new features: parameter check
 - new features: new option "--wp/--with-parameter" for restart
 - new features: support cross version upgrade and rolling upgrade for oceanbase/oceanbase-ce
 - fix bug: can not connect to root when sysbench useing obproxy node
* Fri Dec 31 2021 obd 1.2.0
 - new features: obd mirror disable/enable
 - new features: support obagent 1.1.0
 - new features: parameter check
 - new features: new option "--wp/--with-parameter" for restart
 - new features: support cross version upgrade and rolling upgrade for oceanbase/oceanbase-ce
 - fix bug: can not connect to root when sysbench useing obproxy node
* Thu Sep 30 2021 obd 1.1.1
 - new features: obd test tych
 - new features: new keyword "depends" for configuration file
 - new features: new option "--wop/--without-parameter" for start/restart
 - new features: a daemon will be started when obproxy is started
 - new features: support obagent
 - fix bug: fail to get devname when devname length more than 5
* Mon Aug 09 2021 obd 1.1.0
 - new features: obd cluster autdeploy
 - new features: obd cluster tenant
 - new features: obd test sysbench
 - enhanced startup check
 - new configuration item for redo log
 - start / stop the specified server or component
 - fix bug: proxyro_password and observer_sys_password can not be None
 - more help infomation
* Mon Jun 28 2021 obd 1.0.2
 - fix memory and disk check bug
* Mon Jun 28 2021 obd 1.0.1
 - support configuration password
 - Multi-level checks before start
 - new features: obd cluster upgrade
 - new features: obd update
 - cancel the timeout limit for waiting for the cluster to initialize
 - new configuration item for store log
