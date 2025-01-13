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

from fastapi import APIRouter, Path
from fastapi import BackgroundTasks

from _deploy import UserConfig
from service.api.response import OBResponse
from service.api.response_utils import new_internal_server_error_exception, new_ok_response
from service.model.server import UserInfo
from service.handler import handler_utils


router = APIRouter()


# @router.get("/upgrade/info/{cluster_name}",
#             response_model=OBResponse[ServerInfo],
#             description='get upgrade server info',
#             operation_id='get_upgrade_server_info',
#             tags=['Info'])
# async def get_server_info(cluster_name: str = Path(description="ocp cluster_name")):
#     try:
#         handler = handler_utils.new_server_info_handler()
#         service_info = handler.get_upgrade_cluster_info(cluster_name)
#         if service_info.metadb:
#             service_info.metadb.password = ''
#     except Exception as ex:
#         return new_internal_server_error_exception(ex)
#     return new_ok_response(service_info)


@router.post("/suicide",
            response_model=OBResponse,
            description='exit after a while',
            operation_id='suicide',
            tags=['Process'])
async def suicide(backgroundtasks: BackgroundTasks):
    handler = handler_utils.new_common_handler()
    backgroundtasks.add_task(handler.suicide)
    return new_ok_response("suicide")


@router.get("/get/user",
            response_model=OBResponse[UserInfo],
            description='get system user',
            operation_id='user',
            tags=['User'])
async def get_user():
    username = UserConfig.DEFAULT.get('username')
    return new_ok_response(UserInfo(username=username))
