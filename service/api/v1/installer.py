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
