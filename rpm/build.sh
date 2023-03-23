#!/bin/bash

python_bin='python'
W_DIR=`pwd`
VERSION=${VERSION:-'1.3.3'}


function python_version()
{
    return `$python_bin -c 'import sys; print (sys.version_info.major)'`
}

function ispy3()
{
    python_version
    if [ $? != 3 ]; then
        echo 'need python3'
        exit 1
    fi
}

function ispy2()
{
    python_version
    if [ $? != 2 ]; then
        echo 'need python2'
        exit 1
    fi
}

function cd2workdir()
{
    cd $W_DIR
    DIR=`dirname $0`
    cd $DIR
}
    

function pacakge_executer27()
{
    ispy2
    cd2workdir
    rm -fr executer27
    mkdir -p ./executer27/{site-packages,bin}
    cd executer27
    pip install -r ../../executer27-requirements.txt --target=./site-packages -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com || exit 1
    pyinstaller -F ../../executer27.py
    if [ -e dist/executer27 ]; then
        cp dist/executer27 ./bin/executer
        rm -fr build dist executer27.spec
    else
        exit 1
    fi
}

function pacakge_obd()
{
    ispy3
    cd2workdir
    DIR=`pwd`
    RELEASE=${RELEASE:-'1'}
    export RELEASE=$RELEASE
    export VERSION=$VERSION
    pip install -r ../requirements3.txt
    rm -fr rpmbuild
    mkdir -p rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    rpmbuild --define "_topdir $DIR/rpmbuild" -bb ob-deploy.spec
    rpms=`find rpmbuild/RPMS/ -name ob-deploy-\*` || exit 1
    for rpm in ${rpms[@]}; do
        cp $rpm ./
    done
    rm -fr rpmbuild
}

function package_web()
{
    cd2workdir
    DIR=`pwd`/../web
    cd $DIR
    yarn
    yarn build
}

function get_python()
{
    if [ `id -u` != 0 ] ; then
        echo "Please use root to run"
    fi

    obd_dir=`dirname $0`
    python_path=`which python`
    for bin in ${python_path[@]}; do
        if [ -e $bin ]; then
            python_bin=$bin
            break 1
        fi
    done

    if [ ${#python_path[*]} -gt 1 ]; then
        read -p "Enter python path [default $python_bin]:"
        if [ "x$REPLY" != "x" ]; then
            python_bin=$REPLY
        fi
    fi
}

function build()
{
    python_version
    if [ $? != 2 ]; then
        req_fn='requirements3'
    else
        req_fn='requirements'
    fi
    cd2workdir
    DIR=`pwd`
    cd ..
    if [ `git log |head -n1 | awk -F' ' '{print $2}'` ]; then
        CID=`git log |head -n1 | awk -F' ' '{print $2}'`
        BRANCH=`git rev-parse --abbrev-ref HEAD`
    else
        CID='UNKNOWN'
        BRANCH='UNKNOWN'
    fi
    DATE=`date '+%b %d %Y %H:%M:%S'`
    VERSION="$VERSION".`date +%s`
    BUILD_DIR="$DIR/.build"
    rm -fr $BUILD_DIR
    mkdir -p $BUILD_DIR/lib/site-packages
    mkdir -p $BUILD_DIR/mirror/remote
    wget https://mirrors.aliyun.com/oceanbase/OceanBase.repo -O $BUILD_DIR/mirror/remote/OceanBase.repo
    cat _cmd.py | sed "s/<CID>/$CID/" | sed "s/<B_BRANCH>/$BRANCH/" | sed "s/<B_TIME>/$DATE/" | sed "s/<DEBUG>/$OBD_DUBUG/" | sed "s/<VERSION>/$VERSION/" > obd.py
    sed -i "s|<DOC_LINK>|$OBD_DOC_LINK|" _errno.py
    pip install -r $req_fn.txt || exit 1
    pip install -r plugins-$req_fn.txt --target=$BUILD_DIR/lib/site-packages || exit 1
    pyinstaller --hidden-import=decimal --hidden-import=configparser -F obd.py || exit 1
    rm -f obd.py obd.spec
    cp -r plugins $BUILD_DIR/plugins
    cp -r config_parser $BUILD_DIR/config_parser
    rm -fr $BUILD_DIR/plugins/oceanbase-ce
    rm -fr $BUILD_DIR/config_parser/oceanbase-ce
    rm -fr /usr/obd /usr/bin/obd
    cp ./dist/obd /usr/bin/obd 
    cp -fr ./profile/* /etc/profile.d/
    rm -fr dist
    cd $BUILD_DIR/plugins && ln -s oceanbase oceanbase-ce && cp -rf obproxy/3.1.0 obproxy-ce/ && cp -rf $DIR/plugins/obproxy-ce/* obproxy-ce/
    cd $BUILD_DIR/config_parser && ln -s oceanbase oceanbase-ce
    mv $BUILD_DIR /usr/obd
    chmod +x /usr/bin/obd
    chmod -R 755 /usr/obd/*
    chown -R root:root /usr/obd/*
    find /usr/obd -type f -exec chmod 644 {} \;
    echo -e 'Installation of obd finished successfully\nPlease source /etc/profile.d/obd.sh to enable it'
}

case "x$1" in
    xexecuter)
        pacakge_executer27
    ;;
    xrpm_obd)
        pacakge_obd
    ;;
    xrpm-all);&
	xrpm)
        pacakge_executer27
        $2
        pacakge_obd
    ;;
    xbuild_obd)
        build
    ;;
    xbuild)
        get_python
        pacakge_executer27
        $2
        get_python
        build
    ;;
    xweb)
        package_web
    ;;
esac
