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
from fastapi import APIRouter, Path, Query, BackgroundTasks, Request

from service.api import response_utils
from service.api.response import OBResponse, DataList
from service.handler import handler_utils
from service.model.deployments import DeploymentConfig, PreCheckResult, RecoverChangeParameter, TaskInfo, \
    ConnectionInfo, InstallLog, Deployment, DeploymentInfo, DeploymentReport, DeploymentStatus, ScenarioType, \
    CreateTenantConfig, CreateTenantLog

router = APIRouter()


@router.post("/deployments/{name}",
             response_model=OBResponse,
             description='create deployment config',
             operation_id='createDeploymentConfig',
             tags=['Deployments'])
async def create_deployment(name: str = Path(description='name'),
                            config: DeploymentConfig = ...):
    handler = handler_utils.new_deployment_handler()
    cluster = None
    try:
        oceanbase_config_path = handler.generate_deployment_config(name, config)
        cluster = handler.create_deployment(name, oceanbase_config_path)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    if cluster:
        return response_utils.new_ok_response(cluster)
    else:
        return response_utils.new_bad_request_exception(Exception('deployment {0} already exists'.format(name)))


@router.post("/deployments/{name}/precheck",
             response_model=OBResponse,
             description='pre-check, asynchronous process',
             operation_id='pre-check',
             tags=['Deployments'])
async def pre_check(name: str, background_tasks: BackgroundTasks):
    handler = handler_utils.new_deployment_handler()
    try:
        handler.precheck(name, background_tasks)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response("precheck for {0}".format(name))


@router.get("/deployments/{name}/precheck",
            response_model=OBResponse[PreCheckResult],
            description='select pre-check status by pre deployment name',
            operation_id='preCheckStatus',
            tags=['Deployments'])
async def get_pre_check_status(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    precheck_result = handler.get_precheck_result(name)
    return response_utils.new_ok_response(precheck_result)


@router.post("/deployments/{name}/recover",
             response_model=OBResponse[DataList[RecoverChangeParameter]],
             description='recover',
             operation_id='recover',
             tags=['Deployments'])
async def recover(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    try:
        recover_result = handler.recover(name)
        return response_utils.new_ok_response(recover_result)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)


@router.post("/deployments/{name}/install",
             response_model=OBResponse,
             description='deploy and start a deployment',
             operation_id='deployAndStartADeployment',
             tags=['Deployments'])
async def install(name: str, background_tasks: BackgroundTasks):
    handler = handler_utils.new_deployment_handler()
    try:
        handler.install(name, background_tasks)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response("")


@router.get("/deployments/{name}/install",
            response_model=OBResponse[TaskInfo],
            description='query install status',
            operation_id='queryInstallStatus',
            tags=['Deployments'])
async def get_install_status(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_install_task_info(name)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(name))
    return response_utils.new_ok_response(task_info)


@router.post("/deployments/{name}/start",
             response_model=OBResponse,
             description='start a deployment',
             operation_id='startADeployment',
             tags=['Deployments'])
async def start(name: str, background_tasks: BackgroundTasks):
    handler = handler_utils.new_deployment_handler()
    try:
        handler.start(name, background_tasks)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response("")

@router.get("/deployments/{name}/start",
            response_model=OBResponse[TaskInfo],
            description='query start status',
            operation_id='queryStartStatus',
            tags=['Deployments'])
async def get_start_status(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_start_task_info(name)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(name))
    return response_utils.new_ok_response(task_info)

@router.get("/deployments/{name}/start/log",
            response_model=OBResponse[InstallLog],
            description='query start log',
            operation_id='queryStartLog',
            tags=['Deployments'])
async def get_start_log(name: str = Path(description='deployment name'),
                          offset: int = Query(None, description='log offset'),
                          component_name: str = Query(None, description='component name')):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_start_task_info(name)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(name))
    origin_log = handler.buffer.read() if component_name is None else handler.get_install_log_by_component(component_name)
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    log_info = InstallLog(log=masked_log[offset:], offset=len(masked_log))
    return response_utils.new_ok_response(log_info)


@router.post("/deployments/{name}/stop",
             response_model=OBResponse,
             description='stop a deployment',
             operation_id='stopADeployment',
             tags=['Deployments'])
async def stop(name: str, background_tasks: BackgroundTasks):
    handler = handler_utils.new_deployment_handler()
    try:
        handler.stop(name, background_tasks)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response("")

@router.get("/deployments/{name}/stop",
            response_model=OBResponse[TaskInfo],
            description='query stop status',
            operation_id='queryStopStatus',
            tags=['Deployments'])
async def get_start_status(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_stop_task_info(name)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(name))
    return response_utils.new_ok_response(task_info)

@router.get("/deployments/{name}/stop/log",
            response_model=OBResponse[InstallLog],
            description='query stop log',
            operation_id='queryStopLog',
            tags=['Deployments'])
async def get_stop_log(name: str = Path(description='deployment name'),
                          offset: int = Query(None, description='log offset'),
                          component_name: str = Query(None, description='component name')):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_stop_task_info(name)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(name))
    origin_log = handler.buffer.read() if component_name is None else handler.get_install_log_by_component(component_name)
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    log_info = InstallLog(log=masked_log[offset:], offset=len(masked_log))
    return response_utils.new_ok_response(log_info)

@router.get("/deployments/{name}/connection",
            response_model=OBResponse[DataList[ConnectionInfo]],
            description='query connect info',
            operation_id='queryConnectionInfo',
            tags=['Deployments'])
async def get_connect_info(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    connection_info_list = handler.list_connection_info(name)
    if connection_info_list is None:
        return response_utils.new_not_found_exception(Exception("deployment {0} not found".format(name)))
    else:
        return response_utils.new_ok_response(connection_info_list)


@router.get("/deployments/{name}/install/log",
            response_model=OBResponse[InstallLog],
            description='query install log',
            operation_id='queryInstallLog',
            tags=['Deployments'])
async def get_install_log(name: str = Path(description='deployment name'),
                          offset: int = Query(None, description='log offset'),
                          component_name: str = Query(None, description='component name')):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_install_task_info(name)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(name))
    origin_log = handler.buffer.read() if component_name is None else handler.get_install_log_by_component(component_name)
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    log_info = InstallLog(log=masked_log[offset:], offset=len(masked_log))
    return response_utils.new_ok_response(log_info)


@router.get("/deployments",
            response_model=OBResponse[DataList[Deployment]],
            description='get deployment',
            operation_id='getDeployment',
            tags=['Deployments'])
async def get_deployments(task_status: DeploymentStatus = Query(..., description='task status,ex:INSTALLING,DRAFT')):
    handler = handler_utils.new_deployment_handler()
    deployments = handler.list_deployments_by_status(task_status)
    return response_utils.new_ok_response(deployments)


@router.get("/deployments/{name}/detail",
             response_model=OBResponse,
             description='get one deployment detail',
             operation_id='queryDeploymentDetail',
             tags=['Deployments'])
async def get_detail(name: str, background_tasks: BackgroundTasks):
    handler = handler_utils.new_deployment_handler()
    deployment = handler.get_deployment_detail_by_name(name)
    if deployment is None:
        return response_utils.new_not_found_exception(Exception('deployment {} not found'.format(name)))
    return response_utils.new_ok_response(deployment)


@router.get("/deployments/{name}",
            response_model=OBResponse[DeploymentInfo],
            description='query deployment config',
            operation_id='queryDeploymentConfig',
            tags=['Deployments'])
async def get_deployment(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    deployment = handler.get_deployment_by_name(name)
    if deployment is None:
        return response_utils.new_not_found_exception(Exception('deployment {} not found'.format(name)))
    return response_utils.new_ok_response(deployment)


@router.get("/deployments/{name}/report",
            response_model=OBResponse[DataList[DeploymentReport]],
            description='query deployment report',
            operation_id='queryDeploymentReport',
            tags=['Deployments'])
async def get_deployment_report(name: str = Path(description='deployment name')):
    handler = handler_utils.new_deployment_handler()
    try:
        report_list = handler.get_deployment_report(name)
    except Exception as ex:
        raise response_utils.new_bad_request_exception(ex)
    return response_utils.new_ok_response(report_list)


@router.delete("/deployments/{name}",
            response_model=OBResponse,
            description='destroy deployment ',
            operation_id='destroyDeployment ',
            tags=['Deployments'])
async def destroy_deployment(name: str, background_tasks: BackgroundTasks):
    handler = handler_utils.new_deployment_handler()
    background_tasks.add_task(handler.destroy_cluster, name)
    return response_utils.new_ok_response("")


@router.get("/deployments/{name}/destroy",
            response_model=OBResponse[TaskInfo],
            description='get destroy task info',
            operation_id='getDestroyTaskInfo',
            tags=['Deployments'])
async def get_destroy_task_info(name: str):
    handler = handler_utils.new_deployment_handler()
    info = handler.get_destroy_task_info(name)
    return response_utils.new_ok_response(info)


@router.get("/deployments/scenario/type",
            response_model=OBResponse[DataList[ScenarioType]],
            description='get scenario',
            operation_id='getScenario',
            tags=['Deployments'])
async def get_destroy_task_info(
        request: Request,
        version: str = Query(None, description='ob version')
):
    headers = request.headers
    language = headers.get('accept-language')
    handler = handler_utils.new_deployment_handler()
    info = handler.get_scenario_by_version(version, language)
    return response_utils.new_ok_response(info)


@router.get("/deployments_test",
            response_model=OBResponse,
            description='get destroy task info',
            operation_id='getDestroyTaskInfo',
            tags=['Deployments'])
async def get_destroy_task_info():

    return response_utils.new_ok_response('inknnsdlafasd')

@router.get("/deployments/{name}/unitresource",
             response_model=OBResponse,
             description='unit resource',
             operation_id='unitResource',
             tags=['Deployments'])
async def unit_resource(name: str):
    handler = handler_utils.new_deployment_handler()
    try:
        unit_resource = handler.unit_resource(name)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(unit_resource)


@router.post("/deployments/{name}/tenants",
             response_model=OBResponse,
             description='create tenant',
             operation_id='createTenant',
             tags=['Deployments'])
async def create_tenant(background_tasks: BackgroundTasks, config: CreateTenantConfig, name: str):
    handler = handler_utils.new_deployment_handler()
    handler.buffer.clear()
    try:
        task_info = handler.create_tenant(name, background_tasks, config)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(task_info)


@router.get("/deployments/{name}/tenants/{task_id}",
             response_model=OBResponse,
             description='create tenant task info',
             operation_id='createTenantTaskInfo',
             tags=['Deployments'])
async def get_create_tenant_task(task_id: int = Path(description="create tenant task id")):
    handler = handler_utils.new_deployment_handler()
    try:
        task_info = handler.get_create_tenant_task_info(task_id)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)
    return response_utils.new_ok_response(task_info)


@router.get("/deployments/{name}/tenants/{task_id}/log",
            response_model=OBResponse[InstallLog],
            description='query create tenant log',
            operation_id='queryCreateTenantLog',
            tags=['Deployments'])
async def get_install_log(offset: int = Query(None, description='log offset'),
                          task_id: int = Path(description="create tenant task id"),
                          detail_log: bool = Query(False, description="detail log")):
    handler = handler_utils.new_deployment_handler()
    task_info = handler.get_create_tenant_task_info(task_id)
    if task_info is None:
        return response_utils.new_not_found_exception("task {0} not found".format(task_id))
    trace_id = handler.context['create_tenant_trace'][task_id]
    origin_log = handler.buffer.read() if not detail_log else handler.get_log_by_trace_id(trace_id)
    masked_log = handler.obd.stdio.table_log_masking(handler.obd.stdio.log_masking(origin_log))
    log_info = CreateTenantLog(log=masked_log[offset:], offset=len(masked_log))
    return response_utils.new_ok_response(log_info)


@router.get("/deployments/{name}/scenario",
            response_model=OBResponse[DataList[ScenarioType]],
            description='get tenant scenario',
            operation_id='getTenantScenario',
            tags=['Deployments'])
async def get_tenant_scenario(name: str):
    handler = handler_utils.new_deployment_handler()
    info = handler.get_tenant_scenario(name)
    return response_utils.new_ok_response(info)
