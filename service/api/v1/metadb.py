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
#
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



