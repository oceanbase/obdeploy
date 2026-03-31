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
#
# OceanBase Deploy (OBD) macOS Installation Script
# This script installs OBD from the extracted tar.gz package.
#
# Package layout (mirrors RPM file.txt):
#   etc/profile.d/obd.sh
#   usr/bin/obd                        -> symlink to ../obd/bin/obd
#   usr/obd/bin/                       -> OBD binary (PyInstaller -D output)
#   usr/obd/config_parser/
#   usr/obd/example/
#   usr/obd/lib/site-packages/
#   usr/obd/mirror/
#   usr/obd/optimize/
#   usr/obd/plugins/
#   usr/obd/workflows/
#
# Installed layout (with /usr/local prefix on macOS):
#   /usr/local/bin/obd                 -> symlink to ../obd/bin/obd
#   /usr/local/obd/                    -> all OBD data
#   /usr/local/etc/profile.d/obd.sh    -> shell completion
#

set -e

# macOS installation prefix
PREFIX="/usr/local"

INSTALL_BIN_DIR="${PREFIX}/bin"
INSTALL_OBD_DIR="${PREFIX}/obd"
PROFILE_DIR="${PREFIX}/etc/profile.d"
CHOWN_GROUP="root:wheel"

# Get the directory where this script is located (extracted package root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing OceanBase Deploy (OBD) ..."
echo "  Binary:  ${INSTALL_BIN_DIR}/obd"
echo "  Home:    ${INSTALL_OBD_DIR}/"
echo "  Profile: ${PROFILE_DIR}/obd.sh"
echo ""

# Check for root/sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "Warning: Running without root privileges. You may need 'sudo ./install.sh'."
    echo "Attempting installation anyway..."
    echo ""
fi

# Remove old installation if exists
rm -rf ${INSTALL_OBD_DIR}
rm -f ${INSTALL_BIN_DIR}/obd

# Create target directories
mkdir -p ${INSTALL_BIN_DIR}
mkdir -p ${INSTALL_OBD_DIR}
mkdir -p ${PROFILE_DIR}

# ---- Install usr/obd/ -> /usr/local/obd/ ----
echo "  -> Installing usr/obd/ ..."
\cp -rf ${SCRIPT_DIR}/usr/obd/* ${INSTALL_OBD_DIR}/

# ---- Install usr/bin/obd -> /usr/local/bin/obd (symlink) ----
echo "  -> Installing usr/bin/obd ..."
ln -sf ../obd/bin/obd ${INSTALL_BIN_DIR}/obd

# ---- Install etc/profile.d/ -> /usr/local/etc/profile.d/ ----
echo "  -> Installing etc/profile.d/ ..."
\cp -rf ${SCRIPT_DIR}/etc/profile.d/* ${PROFILE_DIR}/

# ---- Set permissions ----
echo "  -> Setting permissions ..."
chmod -R 755 ${INSTALL_OBD_DIR}/*
find ${INSTALL_OBD_DIR} -type f -exec chmod 644 {} \;
# Restore executable permission on binary and shared libraries
chmod +x ${INSTALL_OBD_DIR}/bin/obd
find ${INSTALL_OBD_DIR}/bin -name "*.so" -exec chmod 755 {} \; 2>/dev/null
find ${INSTALL_OBD_DIR}/bin -name "*.dylib" -exec chmod 755 {} \; 2>/dev/null
find ${INSTALL_OBD_DIR}/bin/_internal -type f -perm +0111 -exec chmod 755 {} \; 2>/dev/null

# Set ownership if running as root
if [ "$(id -u)" -eq 0 ]; then
    chown -R ${CHOWN_GROUP} ${INSTALL_OBD_DIR}
fi

# Warm up: run once in background to populate OS page cache (faster subsequent launches)
${INSTALL_BIN_DIR}/obd --version > /dev/null 2>&1 &

echo ""
echo "=========================================="
echo "Installation of OBD finished successfully!"
echo "=========================================="
echo ""
echo "Please source the profile to enable shell completion:"
echo "  source ${PROFILE_DIR}/obd.sh"
echo ""
echo "Or add it to your shell profile permanently:"
echo "  echo 'source ${PROFILE_DIR}/obd.sh' >> ~/.zshrc"
echo ""
echo "Verify installation:"
echo "  obd --version"
