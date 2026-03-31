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

PROJECT_DIR=$1
PROJECT_NAME=$2
VERSION=$3
RELEASE=$4
PYTHON3_SWITCH=$5

if [[ x"$PYTHON3_SWITCH" == x"" ]]; then
    echo "No switch command is provided, so use the default switch command: 'source py-env-activate py311'"
    PYTHON3_SWITCH="source py-env-activate py311"
fi

CURDIR=$PWD
DIR=`dirname $0`
cd $DIR

echo "[BUILD] args: CURDIR=${CURDIR} PROJECT_NAME=${PROJECT_NAME} VERSION=${VERSION} RELEASE=${RELEASE}"

export PROJECT_NAME=${PROJECT_NAME}
export VERSION=${VERSION}
export RELEASE=${RELEASE}
eval "./build.sh rpm '$PYTHON3_SWITCH'"
