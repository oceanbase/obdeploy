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
from typing import List

from fastapi import APIRouter, Path, Query, BackgroundTasks, Body

from service.api.response import OBResponse
from service.handler import handler_utils
from service.model.deployments import TaskInfo
from service.model.task import TaskInfo, PrecheckTaskInfo, TaskLog
from service.model.oms import OmsDeploymentConfig
from service.api import response_utils

router = APIRouter()


@router.get("/oms/docker_images",
            response_model=OBResponse,
            description='get_usable_oms_docker_images',
            operation_id='get_usable_oms_docker_images',
            tags=['oms'])
async def get_usable_oms_docker_images(
        oms_servers: str = Query(description="oms servers"),
        username: str = Query(description="ssh username"),
        password: str = Query(description="ssh password"),
        port: int = Query(description="ssh port")
):
    oms_handler = handler_utils.new_oms_handler()
    try:
        images = oms_handler.get_oms_images(oms_servers, username, password, port)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(images)


@router.post("/oms/generate_config/{name}",
             response_model=OBResponse,
             description='create oms deployment config',
             operation_id='create_oms_deployment_config',
             tags=['oms'])
async def create_deployment(name: str = Path(description='name'),
                            config: OmsDeploymentConfig = ...):
    handler = handler_utils.new_oms_handler()
    try:
        config_path = handler.create_oms_config_path(config)
        cluster = handler.create_deployment(name, config_path)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if cluster:
        return response_utils.new_ok_response(cluster)
    else:
        return response_utils.new_bad_request_exception(Exception('deployment {0} already exists'.format(name)))


@router.post("/oms/deployments/{id}/precheck",
             response_model=OBResponse[TaskInfo],
             description='precheck for oms deployment',
             operation_id='precheck_oms_deployment',
             tags=['oms'])
async def precheck_oms_deployment(background_tasks: BackgroundTasks,
                                  id: int = Path(description="deployment id")):
    try:
        handler = handler_utils.new_oms_handler()
        ret = handler.oms_precheck(id, background_tasks)
        if not isinstance(ret, TaskInfo) and ret:
            return response_utils.new_internal_server_error_exception(str(ret[1].args[0]))
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(ret)


@router.get("/oms/deployments/{id}/precheck/{task_id}",
            response_model=OBResponse[PrecheckTaskInfo],
            description='precheck for oms deployment',
            operation_id='precheck_oms',
            tags=['oms'])
async def get_oms_precheck_task(id: int = Path(description="deployment id"),
                                task_id: int = Path(description="task id")):
    handler = handler_utils.new_oms_handler()
    try:
        precheck_result = handler.get_precheck_result(id, task_id)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(precheck_result)


@router.post("/oms/deployments/{id}/install",
             response_model=OBResponse[TaskInfo],
             description='install oms',
             operation_id='install_oms',
             tags=['oms'])
async def install_oms(background_tasks: BackgroundTasks, id: int = Path(description="deployment id")):
    handler = handler_utils.new_oms_handler()
    ret = handler.install(id, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/oms/deployments/{id}/install/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get oms install task',
            operation_id='get_oms_install_task',
            tags=['oms'])
async def get_oms_install_task(id: int = Path(description="deployment id"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_oms_handler()
    task_info = handler.get_install_task_info(id, task_id)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    return response_utils.new_ok_response(task_info)


@router.get("/oms/deployments/{id}/install/{task_id}/log",
            response_model=OBResponse[TaskLog],
            description='get oms install task log',
            operation_id='get_oms_install_task_log',
            tags=['oms'])
async def get_oms_install_task_log(id: int = Path(description="deployment id"),
                                   task_id: int = Path(description="task id"),
                                   offset: int = Query(0, description="offset to read task log")):
    handler = handler_utils.new_oms_handler()
    task_info = handler.get_install_task_info(id, task_id)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    origin_log = handler.buffer.read()
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    return response_utils.new_ok_response(TaskLog(log=masked_log, offset=offset))


@router.post("/oms/deployments/{id}/reinstall",
             response_model=OBResponse[TaskInfo],
             description='reinstall oms',
             operation_id='reinstall_oms',
             tags=['oms'])
async def reinstall_oms(background_tasks: BackgroundTasks, id: int = Path(description="deployment id")):
    handler = handler_utils.new_oms_handler()
    ret = handler.reinstall(id, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/oms/deployments/{id}/reinstall/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get oms reinstall task',
            operation_id='get_oms_reinstall_task',
            tags=['oms'])
async def get_oms_reinstall_task(id: int = Path(description="deployment id"),
                                 task_id: int = Path(description="task id")):
    handler = handler_utils.new_oms_handler()
    task_info = handler.get_reinstall_task_info(id, task_id)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    return response_utils.new_ok_response(task_info)


@router.get("/oms/deployments/{id}/reinstall/{task_id}/log",
            response_model=OBResponse[TaskLog],
            description='get oms reinstall task log',
            operation_id='get_oms_reinstall_task_log',
            tags=['oms'])
async def get_oms_reinstall_task_log(id: int = Path(description="deployment id"),
                                     task_id: int = Path(description="task id"),
                                     offset: int = Query(0, description="offset to read task log")):
    handler = handler_utils.new_oms_handler()
    task_info = handler.get_reinstall_task_info(id, task_id)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(id))
    origin_log = handler.buffer.read()
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    return response_utils.new_ok_response(TaskLog(log=masked_log, offset=offset))


@router.delete("/oms/deployments/{id}",
               response_model=OBResponse[TaskInfo],
               description='destroy oms',
               operation_id='destroy_oms',
               tags=['oms'])
async def destroy_oms(id: int, background_tasks: BackgroundTasks):
    handler = handler_utils.new_oms_handler()
    try:
        info = handler.destroy(id, background_tasks)
    except Exception as ex:
        raise response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(info)


@router.get("/oms/deployments/{id}/destroy/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get oms destroy task',
            operation_id='get_oms_destroy_task',
            tags=['oms'])
async def get_oms_destroy_task(background_tasks: BackgroundTasks,
                               id: int = Path(description="deployment id"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_oms_handler()
    info = handler.get_destroy_task_info(id, task_id)
    if not isinstance(info, TaskInfo):
        return response_utils.new_internal_server_error_exception(info[1])
    return response_utils.new_ok_response(info)


@router.get("/oms/deployments",
            response_model=OBResponse,
            description='get oms deployments',
            operation_id='get_oms_deployments',
            tags=['oms'])
async def get_oms_deployments():
    handler = handler_utils.new_oms_handler()
    deploys = handler.list_oms_deployments()
    return response_utils.new_ok_response(deploys)


@router.get("/oms/upgrade/{name}/info",
            response_model=OBResponse,
            description='get upgrade info',
            operation_id='get_upgrade_info',
            tags=['oms'])
async def get_oms_upgrade_info(name: str = Path(description='name')):
    handler = handler_utils.new_oms_handler()
    try:
        images = handler.get_upgrade_info(name)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(images)


@router.post("/oms/{cluster_name}/upgrade/precheck",
             response_model=OBResponse[TaskInfo],
             description='precheck for oms upgrade',
             operation_id='precheck_oms_upgrade',
             tags=['oms'])
async def precheck_oms_upgrade(background_tasks: BackgroundTasks,
                               cluster_name: str = Path(description="deployment cluster_name"),
                               default_oms_files_path: str = Query(description="oms upgrade default_oms_files_path")):
    handler = handler_utils.new_oms_handler()
    ret = handler.upgrade_precheck(cluster_name, background_tasks, default_oms_files_path)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/oms/{cluster_name}/upgrade/precheck/{task_id}",
            response_model=OBResponse[PrecheckTaskInfo],
            description='get precheck for oms upgrade',
            operation_id='get_oms_upgrade_precheck_task',
            tags=['oms'])
async def get_oms_upgrade_precheck_task(cluster_name: str = Path(description="oms cluster_name"),
                                        task_id: int = Path(description="task id")):
    handler = handler_utils.new_oms_handler()
    try:
        precheck_result = handler.get_upgrade_precheck_result(cluster_name, task_id)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(precheck_result)


@router.post("/oms/{cluster_name}/upgrade",
             response_model=OBResponse[TaskInfo],
             description='upgrade oms',
             operation_id='upgrade_oms',
             tags=['oms'])
async def upgrade_oms(
        background_tasks: BackgroundTasks,
        cluster_name: str = Path(description="oms cluster_name"),
        version: str = Query(description="oms upgrade version"),
        image_name: str = Query('', description="oms upgrade image_name"),
        upgrade_mode: str = Query('', description="oms upgrade mode")
):
    handler = handler_utils.new_oms_handler()
    ret = handler.upgrade_oms(cluster_name, version, image_name, upgrade_mode, background_tasks)
    if not isinstance(ret, TaskInfo) and ret:
        return response_utils.new_internal_server_error_exception(ret[1])
    return response_utils.new_ok_response(ret)


@router.get("/oms/{cluster_name}/upgrade/{task_id}",
            response_model=OBResponse[TaskInfo],
            description='get oms upgrade task',
            operation_id='get_oms_upgrade_task',
            tags=['oms'])
async def get_oms_upgrade_task(cluster_name: str = Path(description="oms cluster_name"),
                               task_id: int = Path(description="task id")):
    handler = handler_utils.new_oms_handler()
    task_info = handler.get_oms_upgrade_task(task_id)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(cluster_name))
    return response_utils.new_ok_response(task_info)


@router.get("/oms/{cluster_name}/upgrade/{task_id}/log",
            response_model=OBResponse[TaskLog],
            description='get oms upgrade task log',
            operation_id='get_oms_upgrade_task_log',
            tags=['oms'])
async def get_oms_upgrade_task_log(cluster_name: str = Path(description="oms cluster_name"),
                                   task_id: int = Path(description="task id"),
                                   offset: int = Query(0, description="offset to read task log")):
    handler = handler_utils.new_oms_handler()
    task_info = handler.get_oms_upgrade_task(task_id)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(cluster_name))
    origin_log = handler.buffer.read()
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    return response_utils.new_ok_response(TaskLog(log=masked_log, offset=offset))


@router.post("/oms/{cluster_name}/takeover",
             response_model=OBResponse,
             description='takeover oms',
             operation_id='takeover_oms',
             tags=['oms'])
async def takeover_oms(cluster_name: str = Path(description="oms cluster_name"),
                       host: str = Body(description="oms container host"),
                       container_name: str = Body(description="oms container name"),
                       user: str = Body(description="ssh user"),
                       password: str = Body(description="ssh password"),
                       port: int = Body(22, description="ssh port")):
    handler = handler_utils.new_oms_handler()
    ret = handler.takeover_oms(cluster_name, host, container_name, user, password, port)
    return response_utils.new_ok_response(ret)


@router.get("/oms/display",
            response_model=OBResponse,
            description='get oms login url',
            operation_id='get_oms_login_url',
            tags=['oms'])
async def get_usable_oms_docker_images():
    handler = handler_utils.new_oms_handler()
    ret = handler.display()
    return response_utils.new_ok_response(ret)


@router.post("/oms/meta/backup",
            response_model=OBResponse,
            description='backup oms',
            operation_id='backup_oms',
            tags=['oms'])
async def backup_oms(backup_path: str = Query(..., description="backup path"),
                    pre_check: bool = Query(False, description="backup pre check")):
    handler = handler_utils.new_oms_handler()
    ret = handler.meta_info_backup(backup_path, pre_check)
    return response_utils.new_ok_response(ret)
