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