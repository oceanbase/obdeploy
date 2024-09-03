# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.

from fastapi import APIRouter, Path, Query, BackgroundTasks, Body
from typing import List

from service.api import response_utils
from service.api.response import OBResponse, DataList
from service.handler import handler_utils
from service.model.deployments import TaskInfo
from service.model.deployments import InstallLog, PreCheckResult
from service.model.metadb import RecoverChangeParameter
from service.model.service_info import DeployName
from service.model.component_change import ComponentChangeMode, ComponentChangeInfo, ComponentChangeConfig, ComponentsChangeInfoDisplay, ComponentsServer, ComponentDepends, ConfigPath

router = APIRouter()


@router.get("/component_change/deployment",
            response_model=OBResponse[DataList[DeployName]],
            description='get scale_out/component_add deployments name',
            operation_id='ComponentChangeDeploymentsName',
            tags=['ComponentChange'])
async def get_deployments():
    try:
        handler = handler_utils.new_component_change_handler()
        deploy_names = handler.get_deployments_name()
        return response_utils.new_ok_response(deploy_names)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)


@router.get("/component_change/deployment/detail",
            response_model=OBResponse[ComponentChangeInfo],
            description='get scale_out/component_add deployments info',
            operation_id='ComponentChangeDeploymentsInfo',
            tags=['ComponentChange'])
async def get_deployments(name=Query(..., description='query deployment name')):
    try:
        handler = handler_utils.new_component_change_handler()
        deploy_info = handler.get_deployment_info(name)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if deploy_info:
        return response_utils.new_ok_response(deploy_info)
    else:
        return response_utils.new_bad_request_exception(Exception(f'Component Change: {name} get deployment info failed'))


@router.get("/component_change/deployment/depends",
            response_model=OBResponse[DataList[ComponentDepends]],
            description='get scale_out/component_add deployments info',
            operation_id='ComponentChangeDeploymentsInfo',
            tags=['ComponentChange'])
async def get_deployment_depends(name=Query(..., description='query deployment name')):
    try:
        handler = handler_utils.new_component_change_handler()
        deploy_info = handler.get_deployment_depends(name)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if deploy_info:
        return response_utils.new_ok_response(deploy_info)
    else:
        return response_utils.new_bad_request_exception(Exception(f'Component Change: {name} get deployment info failed'))


@router.post("/component_change/{name}/deployment",
             response_model=OBResponse,
             description='create scale_out/component_add config',
             operation_id='ComponentChangeConfig',
             tags=['ComponentChange'])
async def create_deployment(
        name: str = Path(description='name'),
        config: ComponentChangeConfig = ...,
):
    handler = handler_utils.new_component_change_handler()
    try:
        path = handler.create_component_change_path(name, config)
        ret = handler.create_component_change_deployment(name, path, config.mode)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if ret:
        return response_utils.new_ok_response(ret)
    else:
        return response_utils.new_bad_request_exception(Exception(f'Component Change: {name} generate config failed'))


@router.post("/component_change/{name}/precheck",
             response_model=OBResponse,
             description='precheck for scale_out/component_add deployment',
             operation_id='PrecheckComponentChange',
             tags=['ComponentChange'])
async def precheck_component_change_deployment(
        background_tasks: BackgroundTasks,
        name: str = Path(description="deployment name")
):
    try:
        handler = handler_utils.new_component_change_handler()
        ret = handler.component_change_precheck(name, background_tasks)
        if not isinstance(ret, TaskInfo) and ret:
            return response_utils.new_internal_server_error_exception(str(ret[1].args[0]))
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(ret)


@router.get("/component_change/{name}/precheck",
            response_model=OBResponse[PreCheckResult],
            description='get result of scale_out/component_add precheck',
            operation_id='PrecheckComponentChangeRes',
            tags=['ComponentChange'])
async def get_component_change_precheck_task(
        name: str = Path(description="deployment name")
):
    handler = handler_utils.new_component_change_handler()
    try:
        precheck_result = handler.get_precheck_result(name)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(precheck_result)


@router.post("/component_change/{name}/recover",
             response_model=OBResponse[DataList[RecoverChangeParameter]],
             description='recover scale_out/component_add config',
             operation_id='RecoverComponentChange',
             tags=['ComponentChange'])
async def recover_deployment(
        name: str = Path(description="deployment name"),
):
    handler = handler_utils.new_component_change_handler()
    try:
        recover_result = handler.recover(name)
        return response_utils.new_ok_response(recover_result)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)


@router.post("/component_change/{name}",
             response_model=OBResponse,
             description='component change',
             operation_id='ComponentChange',
             tags=['ComponentChange'])
async def component_change(
        background_tasks: BackgroundTasks,
        name: str = Path(description="deployment name"),
        mode: ComponentChangeMode = Body(description="mode")
):
    handler = handler_utils.new_component_change_handler()
    if mode.mode == 'add_component':
        handler.add_components(name, background_tasks)
    if mode.mode == 'scale_out':
        handler.scale_out(name, background_tasks)
    return response_utils.new_ok_response(True)


@router.get("/component_change/{name}/component_change",
            response_model=OBResponse[TaskInfo],
            description='get task res of component change',
            operation_id='ComponentChangeTask',
            tags=['ComponentChange'])
async def get_component_change_task(
        name: str = Path(description="deployment name")
):
    handler = handler_utils.new_component_change_handler()
    task_info = handler.get_component_change_task_info(name)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(name))
    return response_utils.new_ok_response(task_info)


@router.get("/component_change/{name}/component_change/log",
            response_model=OBResponse[InstallLog],
            description='get log of component change',
            operation_id='ComponentChangeLog',
            tags=['ComponentChange'])
async def get_component_change_log(
        name: str = Path(description="deployment name"),
        offset: int = Query(0, description="offset to read task log"),
        components: List[str] = Query(None, description='component name')
):
    handler = handler_utils.new_component_change_handler()
    task_info = handler.get_component_change_task_info(name)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(name))
    log_content = handler.buffer.read() if components is None else handler.get_component_change_log_by_component(components, 'add_component')
    log_info = InstallLog(log=log_content[offset:], offset=len(log_content))
    return response_utils.new_ok_response(log_info)


@router.post("/component_change/{name}/display",
               response_model=OBResponse[ComponentsChangeInfoDisplay],
               description='del component with node check',
               operation_id='ComponentChangeNodeCheck',
               tags=['ComponentChange'])
async def get_component_change_detail(
        name: str = Path(description="deployment name"),
):
    handler = handler_utils.new_component_change_handler()
    try:
        info = handler.get_component_change_detail(name)
    except Exception as ex:
        raise response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(info)


@router.post("/component_change/{name}/node/check",
               response_model=OBResponse[ComponentsServer],
               description='del component with node check',
               operation_id='ComponentChangeNodeCheck',
               tags=['ComponentChange'])
async def node_check(
        name: str = Path(description="deployment name"),
        components: List[str] = Query(description="component name"),
):
    handler = handler_utils.new_component_change_handler()
    try:
        info = handler.node_check(name, components)
    except Exception as ex:
        raise response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(info)


@router.delete("/component_change/{name}",
               response_model=OBResponse,
               description='del componnet',
               operation_id='ComponentChangeDelComponent',
               tags=['ComponentChange'])
async def del_component(
        background_tasks: BackgroundTasks,
        name: str = Path(description="deployment name"),
        components: List[str] = Query(description="component name"),
        force: bool = Query(description="force")
):
    handler = handler_utils.new_component_change_handler()
    try:
        info = handler.del_component(name, components, force, background_tasks)
    except Exception as ex:
        raise response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(info)


@router.get("/component_change/{name}/del_component",
            response_model=OBResponse,
            description='get task res of component change',
            operation_id='ComponentChangeTask',
            tags=['ComponentChange'])
async def get_del_component_change_task(
        name: str = Path(description="deployment name"),
):
    handler = handler_utils.new_component_change_handler()
    task_info = handler.get_del_component_task_info(name)
    if not isinstance(task_info, TaskInfo):
        return response_utils.new_internal_server_error_exception("task {0} not found".format(name))
    return response_utils.new_ok_response(task_info)


@router.get("/component_change/{name}/del",
            response_model=OBResponse,
            description='get del component task',
            operation_id='ComponentChangeDelComponentTask',
            tags=['ComponentChange'])
async def get_del_component_log(
        name: str = Path(description="deployment name"),
        offset: int = Query(0, description="offset to read task log"),
        components: List[str] = Query(description="component name"),
):
    handler = handler_utils.new_component_change_handler()
    task_info = handler.get_del_component_task_info(name)
    if task_info is None:
        return response_utils.new_internal_server_error_exception("task {0} not found".format(name))
    log_content = handler.buffer.read() if components is None else handler.get_component_change_log_by_component(components, 'del_component')
    return response_utils.new_ok_response(log_content)


@router.post("/component_change/{name}/remove",
            response_model=OBResponse,
            description='remove component',
            operation_id='RemoveComponent',
            tags=['ComponentChange'])
async def remove_component(
        name: str = Path(description="deployment name"),
        components: List[str] = Query(description="component name List"),
):
    handler = handler_utils.new_component_change_handler()
    info = handler.remove_component(name, components)
    return response_utils.new_ok_response(info)


@router.get("/component_change/{name}/path",
            response_model=OBResponse[ConfigPath],
            description='get config path',
            operation_id='GetConfigPath',
            tags=['ComponentChange'])
async def get_config_path(
        name: str = Path(description="deployment name")
):
    handler = handler_utils.new_component_change_handler()
    info = handler.get_config_path(name)
    return response_utils.new_ok_response(info)