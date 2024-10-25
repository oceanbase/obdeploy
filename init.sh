#!/bin/bash
echo "============prepare work env start============"

if [[ $# == 1 && $1 == "-f" ]]; then
    FORCE_DEPLOY="1"
else
    FORCE_DEPLOY="0"
fi

WORK_DIR=$(readlink -f "$(dirname ${BASH_SOURCE[0]})")

if [ ${OBD_HOME} ]; then
    OBD_HOME=${OBD_HOME}
else
    OBD_HOME="${HOME}/.obd"
fi

if [ ${FORCE_DEPLOY} == "1" ]; then
    rm -rf ${OBD_HOME}/config_parser
    rm -rf ${OBD_HOME}/optimize
    rm -rf ${OBD_HOME}/plugins
    rm -rf ${OBD_HOME}/workflows
    sudo rm -rf /etc/profile.d/obd.sh
fi

if [ ! -e /etc/profile.d/obd.sh ]; then
    sudo ln -s ${WORK_DIR}/profile/obd.sh /etc/profile.d/obd.sh
fi

mkdir -p ${OBD_HOME} && cd ${OBD_HOME}
mkdir -p mirror/remote && cd mirror/remote

if [ ! -e "OceanBase.repo" ]; then
    wget -q https://mirrors.aliyun.com/oceanbase/OceanBase.repo
fi

mkdir -p ${OBD_HOME}/{workflows,plugins,optimize,config_parser}

mkdir -p ${OBD_HOME}/plugins/obproxy-ce/3.1.0

for DIR in ${WORK_DIR}/plugins/obproxy-ce/3.1.0/ ${WORK_DIR}/plugins/obproxy/3.1.0/; do
    FILE_LIST=$(ls $DIR)
    for FILE in $FILE_LIST; do
        if [ ! -e "${OBD_HOME}/plugins/obproxy-ce/3.1.0/${FILE}" ]; then
            ln -s ${DIR}/${FILE} ${OBD_HOME}/plugins/obproxy-ce/3.1.0/${FILE}
        fi
    done
done

for DIR in workflows plugins optimize config_parser; do
    FILE_LIST=$(ls ${WORK_DIR}/${DIR})
    for FILE in $FILE_LIST; do
        if [ ! -e "${OBD_HOME}/${DIR}/${FILE}" ]; then
            ln -s ${WORK_DIR}/${DIR}/${FILE} ${OBD_HOME}/${DIR}/${FILE}
        fi
    done
done

if [ ! -e ${OBD_HOME}/optimize/obproxy-ce ]; then
    ln -s ${OBD_HOME}/optimize/obproxy ${OBD_HOME}/optimize/obproxy-ce
fi

for DIR in workflows plugins config_parser; do
    if [ ! -e ${OBD_HOME}/${DIR}/oceanbase-ce ]; then
        ln -s ${OBD_HOME}/${DIR}/oceanbase ${OBD_HOME}/${DIR}/oceanbase-ce
    fi
    if [ ! -e ${OBD_HOME}/${DIR}/ocp-server-ce ]; then
        ln -s ${OBD_HOME}/${DIR}/ocp-server ${OBD_HOME}/${DIR}/ocp-server-ce
    fi
done

echo -n '<VERSION>' > ${OBD_HOME}/version

echo "============update .bashrc============"

ALIAS_OBD_EXIST=$(grep "alias obd=" ~/.bashrc | head -n 1)

if [[ "${ALIAS_OBD_EXIST}" != "" ]]; then
    echo "need update obd alias"
fi

echo "export OBD_INSTALL_PATH=${WORK_DIR}" >> ~/.bashrc
echo "alias obd='python ${WORK_DIR}/_cmd.py'" >> ~/.bashrc
echo -e "if [ -d ${WORK_DIR} ]\nthen\n    source ${WORK_DIR}/profile/obd.sh\nfi" >> ~/.bashrc

echo "Please enter ob-deploy dir and install python requirements by 'pip install -r requirements.txt' when your python version is '2.x' and replace requirements.txt with requirements3.txt when your python version is '3.x'"

echo "============prepare work env ok!============"
