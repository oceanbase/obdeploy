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
from fastapi import APIRouter, Path, Query, BackgroundTasks

from service.api.response import OBResponse, DataList
from service.api import response_utils
from service.model.metadb import MetadbDeploymentInfo, MetadbDeploymentConfig, DatabaseConnection, RecoverChangeParameter
from service.model.resource import MetaDBResource, ResourceCheckResult
from service.model.task import TaskInfo, PrecheckTaskInfo, TaskLog
from service.handler.handler_utils import new_metadb_handler

router = APIRouter()


@router.post("/metadb/connections",
            response_model=OBResponse[DatabaseConnection],
            description='create metadb connection',
            operation_id='create_metadb_connection',
            tags=['Metadb'])
async def create_metadb_connection(
        sys: bool = Query(False, description='whether the incoming tenant is the sys tenant'),
        metadb_connection: DatabaseConnection = ...
    ):
    handler = new_metadb_handler()
    try:
        connection_info = handler.create_connection_info(metadb_connection, sys)
        return response_utils.new_ok_response(connection_info)
    except Exception as e:
        return response_utils.new_internal_server_error_exception(e)


@router.get("/metadb/connections/{cluster_name}",
            response_model=OBResponse[DatabaseConnection],
            description='get metadb connection',
            operation_id='get_metadb_connection',
            tags=['Metadb'])
async def get_metadb_connection(cluster_name: str = Path(description="cluster name")):
    handler = new_metadb_handler()
    connection_info = handler.get_connection_info(cluster_name)
    if connection_info is None:
        return response_utils.new_internal_server_error_exception(Exception("deployment {0} not found".format(id)))
    else:
        return response_utils.new_ok_response(connection_info)



