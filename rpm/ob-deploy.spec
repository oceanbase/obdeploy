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
%define _build_id_links none


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
cd $SRC_DIR/web
yarn
yarn build
cd $SRC_DIR
sed -i "s/<CID>/$CID/" const.py  && sed -i "s/<B_BRANCH>/$BRANCH/" const.py  && sed -i  "s/<B_TIME>/$DATE/" const.py  && sed -i "s/<DEBUG>/$OBD_DUBUG/" const.py && sed -i "s/<VERSION>/$VERSION/" const.py && sed -i "s/<TELEMETRY_WEBSITE>/$TELEMETRY_WEBSITE/" const.py
cp -f _cmd.py obd.py
sed -i "s|<DOC_LINK>|$OBD_DOC_LINK|" _errno.py
mkdir -p $BUILD_DIR/SOURCES ${RPM_BUILD_ROOT}
mkdir -p $BUILD_DIR/SOURCES/{site-packages}
mkdir -p ${RPM_BUILD_ROOT}/usr/bin
mkdir -p ${RPM_BUILD_ROOT}/usr/obd
pip install -r plugins-requirements3.txt --target=$BUILD_DIR/SOURCES/site-packages  -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
pip install -r service/service-requirements.txt --target=$BUILD_DIR/SOURCES/site-packages  -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
# pyinstaller -y --clean -n obd-web -p $BUILD_DIR/SOURCES/site-packages -F service/app.py
pyinstaller --hidden-import=decimal -p $BUILD_DIR/SOURCES/site-packages --hidden-import service/app.py --hidden-import=configparser -F obd.py
rm -f obd.py obd.spec
\mkdir -p $BUILD_DIR/SOURCES/web
\cp -rf $SRC_DIR/dist/obd ${RPM_BUILD_ROOT}/usr/bin/obd
\cp -rf $SRC_DIR/web/dist $BUILD_DIR/SOURCES/web
\cp -rf $SRC_DIR/plugins $BUILD_DIR/SOURCES/plugins
\cp -rf $SRC_DIR/optimize $BUILD_DIR/SOURCES/optimize
\cp -rf $SRC_DIR/example $BUILD_DIR/SOURCES/example
\cp -rf $SRC_DIR/config_parser $BUILD_DIR/SOURCES/config_parser
\rm -fr $BUILD_DIR/SOURCES/plugins/oceanbase-ce
\rm -fr $BUILD_DIR/SOURCES/config_parser/oceanbase-ce
\cp -rf $SRC_DIR/profile/ $BUILD_DIR/SOURCES/
\cp -rf $SRC_DIR/mirror/ $BUILD_DIR/SOURCES/
\cp -rf $BUILD_DIR/SOURCES/web ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/plugins ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/optimize ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/config_parser ${RPM_BUILD_ROOT}/usr/obd/
\cp -rf $BUILD_DIR/SOURCES/mirror ${RPM_BUILD_ROOT}/usr/obd/
mkdir -p ${RPM_BUILD_ROOT}/etc/profile.d/
\cp -rf $BUILD_DIR/SOURCES/profile/* ${RPM_BUILD_ROOT}/etc/profile.d/
mkdir -p ${RPM_BUILD_ROOT}/usr/obd/lib/
\cp -rf $BUILD_DIR/SOURCES/site-packages ${RPM_BUILD_ROOT}/usr/obd/lib/site-packages
mkdir -p ${RPM_BUILD_ROOT}/usr/obd/lib/executer
\cp -rf ${RPM_DIR}/executer27 ${RPM_BUILD_ROOT}/usr/obd/lib/executer/
\cp -rf $BUILD_DIR/SOURCES/example ${RPM_BUILD_ROOT}/usr/obd/
cd ${RPM_BUILD_ROOT}/usr/obd/plugins && ln -s oceanbase oceanbase-ce && \cp -rf obproxy/3.1.0 obproxy-ce/ && \cp -rf $SRC_DIR/plugins/obproxy-ce/* obproxy-ce/
cd ${RPM_BUILD_ROOT}/usr/obd/plugins && ln -sf ocp-server ocp-server-ce
mv obproxy/3.1.0 obproxy/3.2.1
cd ${RPM_BUILD_ROOT}/usr/obd/config_parser && ln -s oceanbase oceanbase-ce
cd ${RPM_BUILD_ROOT}/usr/obd/optimize && ln -s obproxy obproxy-ce

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
* Fri Nov 24 2023 obd 2.4.0
 - new features: support for graphical deployment of OCP-CE V4.2.1
 - new features: support for graphical deployment of OCP-CE V4.2.1 along with its MetaDB
 - new features: support for command-line deployment of OCP-CE V4.2.1 along with its MetaDB
 - new features: support for upgrading previous versions to OCP-CE V4.2.1
 - new features: compatibility updates for OBDiag V1.4.0 and V1.3.0
 - new features: compatibility with kylin OS
 - enhancements: improved pre-launch checks for OceanBase databases
 - improvements: enhanced error messaging during SQL execution and provide SQL execution Trace
 - bug fixes: fixed an issue where deploying OceanBase V4.2.0 and above with local_ip would still perform NIC checks
 - bug fixes: resolved a RuntimeError that could occur when destroying clusters deployed with OBD versions prior to V2.3.0
 - bug fixes: fixed an issue where edit-config could not exit after enabling IO_DEFAULT_CONFIRM
* Fri Oct 13 2023 obd 2.3.1
 - new features: adapt to OCP Express V4.2.1
 - bug fixes: fix checks during rolling upgrade that did not behave as expected under special circumstances
 - bug fixes: resolve self-upgrade extraction failure of obd on el8 operating systems
 - bug fixes: unexpected exceptions in obd cluster chst with ob-configserver component
 - bug fixes: unexpected exceptions in ob-configserver when connection_url is not configured
* Fri Sep 15 2023 obd 2.3.0
 - new features: support for OceanBase 4.2 network-based primary/standby solution
 - new features: support for ConfigServer
 - new features: support for selecting units for capacity type parameters during web-based graphical deployment
* Wed Aug 02 2023 obd 2.2.0
 - new features: adapt to OceanBase-CE V4.2
 - new features: introduce 19G storage option for small-scale deployment with OceanBase-CE V4.2
 - new features: adapt to OCP Express V4.2
 - new features: web-based graphical deployment now allows for custom component selection
 - optimization: improved OBProxy startup performance on machines with low specs
 - change: redeploy now requires confirmation, can be bypassed with --confirm option
 - change: automatic confirmation for all commands can be enabled with obd env set IO_DEFAULT_CONFIRM 1
 - fix bug: fixed the issue where OCP Express ocp_meta_tenant setting was not effective
 - fix bug: fixed incorrect recognition of custom capacity type parameters in obd demo
* Mon Jun 12 2023 obd 2.1.1
 - new features: support upgrade keyword 'when_come_from' and 'deprecated'
 - fix bug: start server failed when other servers downtime #171
 - fix bug: The signed '%' password causes a stack overflow in the upgrade plugin
 - fix bug: system_memory check failed when memory_limit is 0
 - fix bug: xtend ocp-express meta ob connect time
* Fri May 12 2023 obd 2.1.0
 - new features: support oceanbase-ce V4.0 upgrade
 - new features: support ocp-express V1.0.1
 - new features: support oceanbase-diagnostic-tool
 - new features: random password when password is empty
 - new features: obd web support English
* Mon Apr 24 2023 obd 2.0.1
 - new features: support ocp-express reinstall
 - bug fix: exit code is not 0 when obd test tpcc
 - bug fix: tpcc test failed when the obproxy ce component is not included in the deployment
* Thu Mar 23 2023 obd 2.0.0
 - new features: obd web
 - new features: obd display-trace
 - new features: obd cluster tenant show
 - new features: obd mirror add-repo
 - new features: new option "--generate-consistent-config/--gcc" for autdeploy
 - new features: support ocp-express
 - new features: support obagent V1.3.0
 - new features: support oceanbase-ce V4.1.0
 - bug fix: start when system_memory is greater than memory_limit
 - bug fix: Table 'TEST.LINEITEM' doesn't exist in obd tpch test
* Wed Dec 14 2022 obd 1.6.2
 - new features: support OceanBaseCE BP upgrade
 - fix bug: grafana init failed when remote deploy
* Thu Nov 24 2022 obd 1.6.1
 - new features: minimum startup resource check
 - fix bug: grafana dashboard title
 - fix bug: autodeploy maybe failed in the case of large memory and small disk
 - fix bug: obproxy frequent core dump in demo
 - fix bug: remote install rsync transmission does not use the user.port
* Mon Oct 31 2022 obd 1.6.0
 - new features: support oceanbase 4.0
 - new features: support Prometheus
 - new features: support Grafana
 - new features: obd demo
* Wed Aug 17 2022 obd 1.5.0
 - new features: obd cluster reinstall
 - new features: obd tool
 - new features: support rsync
 - new keyword: include
 - more option: obd test mysqltest
* Sun Jul 17 2022 obd 1.4.0
 - new features: support tpcc
 - new features: support mysqltest record
 - fix bug: tpch ddl
* Tue Apr 26 2022 obd 1.3.3
 - new features: change repository for a deployed component
 - fix bug: check kernel version when autdeploy obproxy
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
