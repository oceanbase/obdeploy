# coding: utf-8
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

from fastapi import APIRouter, Path, Query, BackgroundTasks, Body

from service.api.response import OBResponse, DataList
from service.handler import handler_utils
from service.model.deployments import OCPDeploymnetConfig, PreCheckResult, RecoverChangeParameter, TaskInfo, \
    ConnectionInfo, InstallLog, Deployment, DeploymentInfo, DeploymentReport, DeploymentStatus, UserCheck
from service.model.task import TaskInfo, PrecheckTaskInfo, TaskLog
from service.model.database import DatabaseConnection
from service.model.ocp import OcpInfo, OcpDeploymentInfo, OcpDeploymentConfig, OcpResource, OcpInstalledInfo, OcpUpgradeLostAddress
from service.model.metadb import RecoverChangeParameter
from service.api import response_utils

router = APIRouter()


@router.get("/ocp/info/{id}",
            response_model=OBResponse[OcpInstalledInfo],
            description='get_installed_ocp_info',
            operation_id='get_installed_ocp_info',
            tags=['OCP'])
async def get_installed_ocp_info(id: int = Path(description="deployment id")):
    ocp_handler = handler_utils.new_ocp_handler()
    try:
        info = ocp_handler.get_installed_ocp_info(id)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(info)


@router.post("/ocp_deployments/{name}",
             response_model=OBResponse,
             description='create ocp deployment config',
             operation_id='createOcpDeploymentConfig',
             tags=['OCP'])
async def create_deployment(name: str = Path(description='name'),
                            config: OCPDeploymnetConfig = ...):
    handler = handler_utils.new_ocp_handler()
    cluster = None
    try:
        ocp_config_path = handler.create_ocp_config_path(config)
        cluster = handler.create_ocp_deployment(name, ocp_config_path)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if cluster:
        return response_utils.new_ok_response(cluster)
    else:
        return response_utils.new_bad_request_exception(Exception('deployment {0} already exists'.format(name)))


@router.post("/machine/check/user",
            response_model=OBResponse,
            description='Check if the user input exists',
            operation_id='machineUser',
            tags=['OCP']
            )
async def check_user(user: UserCheck = Body(description='server, port, username, password')):
    handler = handler_utils.new_ocp_handler()
    exist = None
    try:
        exist = handler.check_user(user)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if exist:
        return response_utils.new_ok_response(exist)
    else:
        return response_utils.new_bad_request_exception(Exception('user {0} user/password error'.format(user)))


@router.post("/ocp/deployments/{id}/precheck",
            response_model=OBResponse[TaskInfo],
            description='precheck for ocp deployment',
            operation_id='precheck_ocp_deployment',
            tags=['OCP'])
async def precheck_ocp_deployment(background_tasks: BackgroundTasks,
                                  id: int = Path(description="deployment id")):
    try:
        handler = handler_utils.new_ocp_handler()
        ret = handler.ocp_precheck(id, background_tasks)
        if not isinstance(ret, TaskInfo) and ret:
            return response_utils.new_internal_server_error_exception(str(ret[1].args[0]))
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(ret)


@router.get("/ocp/deployments/{id}/precheck/{task_id}",
            response_model=OBResponse[PrecheckTaskInfo],
            description='precheck for ocp deployment',
            operation_id='precheck_ocp',
            tags=['OCP'])
async def get_ocp_precheck_task(id: int = Path(description="deployment id"),
                                task_id: int = Path(description="task id")):
    handler = handler_utils.new_ocp_handler()
    try:
        precheck_result = handler.get_precheck_result(id, task_id)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(precheck_result)


@router.post("/ocp/deployments/{id}/recover",
            response_model=OBResponse[DataList[RecoverChangeParameter]],
            description='recover ocp deployment config',
            operation_id='recover_ocp_deployment',
            tags=['OCP'])
async def recover_ocp_deployment(id: int = Path(description="deployment id")):
    handler = handler_utils.new_ocp_handler()
    try:
        recover_result = handler.recover(id)
        return response_utils.new_ok_response(recover_result)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)


@router.post("/ocp/deployments/{id}/install",
            response_model=OBResponse[TaskInfo],
            description='install ocp',
            operation_id='install_ocp',
            tags=['OCP'])
async def install_ocp(background_tasks: BackgroundTasks, id: int = Path(description="deployment id")):
    handler = handler_utils.new_ocp_handler()
    ret = handler.install(id, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/ocp/deployments/{id}/install/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get ocp install task',
            operation_id='get_ocp_install_task',
            tags=['OCP'])
async def get_ocp_install_task(id: int = Path(description="deployment id"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_ocp_handler()
    task_info = handler.get_install_task_info(id, task_id)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    return response_utils.new_ok_response(task_info)


@router.get("/ocp/deployments/{id}/install/{task_id}/log",
            response_model=OBResponse[TaskLog],
            description='get ocp install task log',
            operation_id='get_ocp_install_task_log',
            tags=['OCP'])
async def get_ocp_install_task_log(id: int = Path(description="deployment id"),
                                   task_id: int = Path(description="task id"),
                                   offset: int = Query(0, description="offset to read task log")):
    handler = handler_utils.new_ocp_handler()
    task_info = handler.get_install_task_info(id, task_id)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    origin_log = handler.buffer.read()
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    return response_utils.new_ok_response(TaskLog(log=masked_log, offset=offset))


@router.post("/ocp/deployments/{id}/reinstall",
            response_model=OBResponse[TaskInfo],
            description='reinstall ocp',
            operation_id='reinstall_ocp',
            tags=['OCP'])
async def reinstall_ocp(background_tasks: BackgroundTasks, id: int = Path(description="deployment id")):
    handler = handler_utils.new_ocp_handler()
    ret = handler.reinstall(id, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/ocp/deployments/{id}/reinstall/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get ocp reinstall task',
            operation_id='get_ocp_reinstall_task',
            tags=['OCP'])
async def get_ocp_reinstall_task(id: int = Path(description="deployment id"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_ocp_handler()
    task_info = handler.get_reinstall_task_info(id, task_id)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    return response_utils.new_ok_response(task_info)


@router.get("/ocp/deployments/{id}/reinstall/{task_id}/log",
            response_model=OBResponse[TaskLog],
            description='get ocp reinstall task log',
            operation_id='get_ocp_reinstall_task_log',
            tags=['OCP'])
async def get_ocp_reinstall_task_log(id: int = Path(description="deployment id"),
                                   task_id: int = Path(description="task id"),
                                   offset: int = Query(0, description="offset to read task log")):
    handler = handler_utils.new_ocp_handler()
    task_info = handler.get_reinstall_task_info(id, task_id)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    origin_log = handler.buffer.read()
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    return response_utils.new_ok_response(TaskLog(log=masked_log, offset=offset))


@router.delete("/ocp/deployments/{id}",
            response_model=OBResponse[TaskInfo],
            description='destroy ocp',
            operation_id='destroy_ocp',
            tags=['OCP'])
async def destroy_ocp(id: int, background_tasks: BackgroundTasks):
    handler = handler_utils.new_ocp_handler()
    try:
        info = handler.destroy(id, background_tasks)
    except Exception as ex:
        raise response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(info)


@router.get("/ocp/deployments/{id}/destroy/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get ocp destroy task',
            operation_id='get_ocp_destroy_task',
            tags=['OCP'])
async def get_ocp_destroy_task(background_tasks: BackgroundTasks,
                               id: int = Path(description="deployment id"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_ocp_handler()
    info = handler.get_destroy_task_info(id, task_id)
    if not isinstance(info, TaskInfo):
        return response_utils.new_internal_server_error_exception(info[1])
    return response_utils.new_ok_response(info)


@router.post("/ocp",
            response_model=OBResponse[OcpInfo],
            description='create ocp info',
            operation_id='create_ocp_info',
            tags=['OCP'])
async def create_ocp_info(metadb: DatabaseConnection = ...):
    ocp_handler = handler_utils.new_ocp_handler()
    try:
        data = ocp_handler.create_ocp_info(metadb)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(data)


@router.get("/ocp/{cluster_name}",
            response_model=OBResponse[OcpInfo],
            description='get ocp info',
            operation_id='get_ocp_info',
            tags=['OCP'])
async def get_ocp_info(cluster_name: str = Path(description="ocp cluster_name")):
    ocp_handler = handler_utils.new_ocp_handler()
    try:
        data = ocp_handler.get_ocp_info(cluster_name)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(data)


@router.post("/ocp/{cluster_name}/upgrade/precheck",
            response_model=OBResponse[TaskInfo],
            description='post precheck for ocp upgrade',
            operation_id='precheck_ocp_upgrade',
            tags=['OCP'])
async def precheck_ocp_upgrade(background_tasks: BackgroundTasks,
                               cluster_name: str = Path(description="deployment cluster_name")):
    handler = handler_utils.new_ocp_handler()
    ret = handler.upgrade_precheck(cluster_name, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/ocp/{cluster_name}/upgrade/precheck/{task_id}",
            response_model=OBResponse[PrecheckTaskInfo],
            description='get precheck for ocp upgrade',
            operation_id='get_ocp_upgrade_precheck_task',
            tags=['OCP'])
async def get_ocp_upgrade_precheck_task(cluster_name: str = Path(description="ocp cluster_name"),
                                        task_id: int = Path(description="task id")):
    handler = handler_utils.new_ocp_handler()
    try:
        precheck_result = handler.get_upgrade_precheck_result(cluster_name, task_id)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(precheck_result)


@router.post("/ocp/{cluster_name}/upgrade",
            response_model=OBResponse[TaskInfo],
            description='upgrade ocp',
            operation_id='upgrade_ocp',
            tags=['OCP'])
async def upgrade_ocp(
        background_tasks: BackgroundTasks,
        cluster_name: str = Path(description="ocp cluster_name"),
        version: str = Query(description="ocp upgrade version"),
        usable: str = Query('', description="ocp upgrade hash")
):
    handler = handler_utils.new_ocp_handler()
    ret = handler.upgrade_ocp(cluster_name, version, usable, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/ocp/{cluster_name}/upgrade/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get ocp upgrade task',
            operation_id='get_ocp_upgrade_task',
            tags=['OCP'])
async def get_ocp_upgrade_task(cluster_name: str = Path(description="ocp cluster_name"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_ocp_handler()
    task_info = handler.get_ocp_upgrade_task(cluster_name, task_id)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(cluster_name))
    return response_utils.new_ok_response(task_info)


@router.get("/ocp/{cluster_name}/upgrade/{task_id}/log",
            response_model=OBResponse[TaskLog],
            description='get ocp upgrade task log',
            operation_id='get_ocp_upgrade_task_log',
            tags=['OCP'])
async def get_ocp_upgrade_task_log(cluster_name: str = Path(description="ocp cluster_name"),
                                   task_id: int = Path(description="task id"),
                                   offset: int = Query(0, description="offset to read task log")):
    handler = handler_utils.new_ocp_handler()
    task_info = handler.get_ocp_upgrade_task(cluster_name, task_id)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(cluster_name))
    origin_log = handler.buffer.read()
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    return response_utils.new_ok_response(TaskLog(log=masked_log, offset=offset))


@router.get("/ocp/upgraade/agent/hosts",
            response_model=OBResponse[OcpUpgradeLostAddress],
            description='get ocp not upgrading host',
            operation_id='get_ocp_not_upgrading_host',
            tags=['OCP'])
async def get_ocp_upgrade_task_log():
    handler = handler_utils.new_ocp_handler()
    try:
        ret = handler.get_not_upgrade_host()
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(ret)