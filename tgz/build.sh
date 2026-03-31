#!/bin/bash
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

python_bin='python3'
W_DIR=`pwd`
VERSION=${VERSION:-'2.7.0'}
RELEASE=${RELEASE:-'1'}

# macOS install paths (used by install.sh)
INSTALL_BIN_DIR="/usr/local/bin"
INSTALL_OBD_DIR="/usr/local/obd"
PROFILE_DIR="/usr/local/etc/profile.d"

# Cross-platform sed -i wrapper (macOS BSD sed requires '' as backup extension)
sedi() {
    sed -i '' "$@"
}

# Download wrapper (prefer curl on macOS)
download_file() {
    local url="$1"
    local output="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$output"
    elif command -v wget >/dev/null 2>&1; then
        wget "$url" -O "$output"
    else
        echo "Error: neither curl nor wget is available"
        exit 1
    fi
}

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

function cd2workdir()
{
    cd $W_DIR
    DIR=`dirname $0`
    cd $DIR
}

function build_tgz()
{
    ispy3
    cd2workdir
    DIR=`pwd`
    SRC_DIR="$DIR/.."

    cd $SRC_DIR

    # Get git info
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
    STAGE_DIR="$DIR/.stage"
    rm -fr $BUILD_DIR $STAGE_DIR

    mkdir -p $BUILD_DIR/lib/site-packages
    mkdir -p $BUILD_DIR/mirror/remote

    # Download OceanBase.repo
    download_file https://mirrors.aliyun.com/oceanbase/OceanBase.repo $BUILD_DIR/mirror/remote/OceanBase.repo

    # Patch const.py placeholders
    sedi "s/<CID>/$CID/" const.py
    sedi "s/<B_BRANCH>/$BRANCH/" const.py
    sedi "s/<B_TIME>/$DATE/" const.py
    sedi "s/<DEBUG>/$OBD_DUBUG/" const.py
    sedi "s/<VERSION>/$VERSION/" const.py

    # Generate obd.py entry point
    cp -f _cmd.py obd.py
    sedi "s|<DOC_LINK>|$OBD_DOC_LINK|" _errno.py

    # Install dependencies
    pip install -r requirements3.txt || exit 1
    pip install -r plugins-requirements3.txt --target=$BUILD_DIR/lib/site-packages || exit 1

    # Build with PyInstaller -D (directory) mode for faster startup
    pyinstaller --hidden-import=decimal --hidden-import=configparser --hidden-import=yaml -D obd.py || exit 1
    rm -f obd.py obd.spec

    # ---- Assemble data files into BUILD_DIR ----
    \cp -rf plugins $BUILD_DIR/plugins
    \cp -rf workflows $BUILD_DIR/workflows
    \cp -rf config_parser $BUILD_DIR/config_parser
    \cp -rf optimize $BUILD_DIR/optimize
    \cp -rf example $BUILD_DIR/example
    \cp -rf profile $BUILD_DIR/profile

    rm -fr $BUILD_DIR/config_parser/oceanbase-ce

    # Create symlinks in plugins (same as RPM spec)
    cd $BUILD_DIR/plugins
    ln -sf oceanbase oceanbase-ce
    ln -sf oceanbase oceanbase-standalone
    [ -d oceanbase-libs ] && ln -sf oceanbase-libs oceanbase-ce-libs
    [ -d oceanbase-libs ] && ln -sf oceanbase-libs oceanbase-standalone-libs
    [ -d oceanbase-ce-utils ] && ln -sf oceanbase-ce-utils oceanbase-standalone-utils
    [ -d ocp-server ] && ln -sf ocp-server ocp-server-ce
    [ -d obproxy ] && [ -d obproxy-ce ] && \cp -rf obproxy/* obproxy-ce/
    [ -d obproxy-ce ] && \cp -rf $SRC_DIR/plugins/obproxy-ce/* obproxy-ce/ 2>/dev/null
    [ -d oms ] && ln -sf oms oms-ce
    [ -d obbinlog-ce ] && ln -sf obbinlog-ce obbinlog
    [ -d obproxy/3.1.0 ] && mv obproxy/3.1.0 obproxy/3.2.1

    # Create symlinks in workflows
    cd $BUILD_DIR/workflows
    ln -sf oceanbase oceanbase-ce
    ln -sf oceanbase oceanbase-standalone
    [ -d ocp-server ] && ln -sf ocp-server ocp-server-ce
    [ -d obproxy ] && ln -sf obproxy obproxy-ce
    [ -d obbinlog-ce ] && ln -sf obbinlog-ce obbinlog
    [ -d oms ] && ln -sf oms oms-ce
    [ -d obproxy/3.1.0 ] && mv obproxy/3.1.0 obproxy/3.2.1

    # Create symlinks in config_parser
    cd $BUILD_DIR/config_parser
    ln -sf oceanbase oceanbase-ce
    ln -sf oceanbase oceanbase-standalone

    # Create symlinks in optimize
    cd $BUILD_DIR/optimize
    [ -d obproxy ] && ln -sf obproxy obproxy-ce

    # ---- Assemble tar.gz staging directory (mirrors RPM file layout) ----
    #
    # Layout inside tar.gz (following file.txt):
    #   etc/profile.d/obd.sh
    #   usr/bin/obd                        -> symlink to ../obd/bin/obd
    #   usr/obd/bin/obd                    <- PyInstaller -D binary
    #   usr/obd/bin/_internal/             <- PyInstaller -D dependencies
    #   usr/obd/config_parser/
    #   usr/obd/example/
    #   usr/obd/lib/site-packages/
    #   usr/obd/mirror/
    #   usr/obd/optimize/
    #   usr/obd/plugins/
    #   usr/obd/workflows/
    #
    ARCH=$(uname -m)
    PKG_NAME="ob-deploy-${VERSION}-macos-${ARCH}"
    PKG_ROOT="$STAGE_DIR"

    # usr/bin  (binary symlink)
    mkdir -p $PKG_ROOT/usr/bin

    # usr/obd  (all obd data)
    mkdir -p $PKG_ROOT/usr/obd/bin
    mkdir -p $PKG_ROOT/usr/obd/lib

    # etc/profile.d
    mkdir -p $PKG_ROOT/etc/profile.d

    # -- Copy PyInstaller -D output into usr/obd/bin/ --
    \cp -rf $SRC_DIR/dist/obd/* $PKG_ROOT/usr/obd/bin/

    # -- Create usr/bin/obd symlink (relative path to ../obd/bin/obd) --
    cd $PKG_ROOT/usr/bin
    ln -sf ../obd/bin/obd obd

    # -- Copy data directories into usr/obd/ --
    \cp -rf $BUILD_DIR/plugins       $PKG_ROOT/usr/obd/plugins
    \cp -rf $BUILD_DIR/workflows     $PKG_ROOT/usr/obd/workflows
    \cp -rf $BUILD_DIR/config_parser $PKG_ROOT/usr/obd/config_parser
    \cp -rf $BUILD_DIR/optimize      $PKG_ROOT/usr/obd/optimize
    \cp -rf $BUILD_DIR/example       $PKG_ROOT/usr/obd/example
    \cp -rf $BUILD_DIR/mirror        $PKG_ROOT/usr/obd/mirror
    \cp -rf $BUILD_DIR/lib/site-packages $PKG_ROOT/usr/obd/lib/site-packages

    # -- Copy shell profile into etc/profile.d/ --
    \cp -rf $BUILD_DIR/profile/*     $PKG_ROOT/etc/profile.d/

    # -- Copy install script into package root --
    \cp -f $DIR/install.sh $PKG_ROOT/install.sh
    chmod +x $PKG_ROOT/install.sh

    # Clean up build artifacts
    rm -fr $SRC_DIR/dist $SRC_DIR/build

    # Create tar.gz (paths prefixed with ./ e.g. ./usr/bin/obd)
    cd $STAGE_DIR
    tar czf $DIR/${PKG_NAME}.tar.gz .

    # Clean up staging
    rm -fr $STAGE_DIR $BUILD_DIR

    echo ""
    echo "=========================================="
    echo "Build successful!"
    echo "Package: $DIR/${PKG_NAME}.tar.gz"
    echo "=========================================="
    echo ""
    echo "To install:"
    echo "  mkdir ob-deploy && tar xzf ${PKG_NAME}.tar.gz -C ob-deploy"
    echo "  cd ob-deploy && sudo ./install.sh"
}

function get_python()
{
    if [ `id -u` != 0 ] ; then
        echo "Please use root (or sudo) to run"
    fi

    obd_dir=`dirname $0`
    python_path=`which python3 2>/dev/null || which python 2>/dev/null`
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

case "x$1" in
    xbuild)
        get_python
        build_tgz
    ;;
    xbuild_tgz)
        build_tgz
    ;;
    *)
        echo "Usage: $0 {build|build_tgz}"
        echo ""
        echo "  build      - detect python and build tar.gz package"
        echo "  build_tgz  - build tar.gz package directly (requires python3)"
        exit 1
    ;;
esac
