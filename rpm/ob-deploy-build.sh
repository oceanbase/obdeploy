#!/bin/bash

PROJECT_DIR=$1
PROJECT_NAME=$2
VERSION=$3
RELEASE=$4
PYTHON3_SWITCH=$5

if [[ x"$PYTHON3_SWITCH" == x"" ]]; then
    echo "No switch command is provided, so use the default switch command: 'source /environments/python3_env/bin/activate'"
    PYTHON3_SWITCH="source /environments/python3_env/bin/activate"
fi

CURDIR=$PWD

echo "[BUILD] args: CURDIR=${CURDIR} PROJECT_NAME=${PROJECT_NAME} VERSION=${VERSION} RELEASE=${RELEASE}"

export PROJECT_NAME=${PROJECT_NAME}
export VERSION=${VERSION}
export RELEASE=${RELEASE}
eval "./build.sh rpm '$PYTHON3_SWITCH'"
