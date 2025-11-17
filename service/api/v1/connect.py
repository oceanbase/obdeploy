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
from fastapi import APIRouter, Path, Query, BackgroundTasks,Body

from service.api.response import OBResponse, DataList
from service.api import response_utils
from service.handler.connect import ConnectHandler

router = APIRouter()


@router.post("/connect/influxdb",
            response_model=OBResponse,
            description='check influx connect',
            operation_id='check_influx_connect',
            tags=['connect'])
async def create_metadb_connection(
    host: str = Body(..., description="host"),
    port: int = Body(8086, description="port"),
    user: str = Body(..., description="user"),
    password: str = Body(..., description="password")
    ):
    handler = ConnectHandler()
    rv = handler.connect_influxdb(host, port, user, password)
    return response_utils.new_ok_response(rv)






