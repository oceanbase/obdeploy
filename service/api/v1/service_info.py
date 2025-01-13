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
from fastapi import APIRouter, Query, Body

from service.api import response_utils
from service.api.response import OBResponse
from service.handler import handler_utils
from service.model.service_info import ServiceInfo, DeployNames
from service.model.database import DatabaseConnection
from service.model.server import OcpServerInfo

router = APIRouter()


@router.get("/info",
            response_model=OBResponse[ServiceInfo],
            description='get obd info',
            operation_id='getObdInfo',
            tags=['Info'])
async def get_info():
    handler = handler_utils.new_service_info_handler()
    service_info = handler.get_service_info()
    return response_utils.new_ok_response(service_info)


@router.get("/deployment/names",
            response_model=OBResponse[DeployNames],
            description='get deployment names',
            operation_id='getDeploymentNames',
            tags=['Info'])
async def get_deployment_names():
    try:
        handler = handler_utils.new_service_info_handler()
        deploy_names = handler.get_deployments_name()
        return response_utils.new_ok_response(deploy_names)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)


@router.get("/deployment/metadb/connection",
            response_model=OBResponse[DatabaseConnection],
            description='get connection info',
            operation_id='getConnectionInfo',
            tags=['Info'])
async def get_metadb_connection(name: str = Query(..., description='cluster name')):
    try:
        handler = handler_utils.new_service_info_handler()
        metadb = handler.get_metadb_connection(name)
        return response_utils.new_ok_response(metadb)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)

@router.post("/deployment/ocp/agent/ip",
            response_model=OBResponse[OcpServerInfo],
            description='get ocp server info',
            operation_id='getOcpServerInfo',
            tags=['Info'])
async def post_metadb_connection(metadb: DatabaseConnection = Body(..., description='cluster name')):
    try:
        handler = handler_utils.new_service_info_handler()
        metadb = handler.get_component_agent(metadb)
        return response_utils.new_ok_response(metadb)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)


@router.post("/deployment/upgrade/ocp",
            response_model=OBResponse,
            description='get obd info',
            operation_id='create ocp deployment',
            tags=['Info'])
async def create_ocp_deployment(name: str = Query(..., description='cluster name')):
    try:
        handler = handler_utils.new_service_info_handler()
        metadb = handler.create_ocp_info(name)
        return response_utils.new_ok_response(metadb)
    except Exception as ex:
        return response_utils.new_internal_server_error_exception(ex)