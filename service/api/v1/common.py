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
from fastapi import APIRouter, Query

from fastapi import BackgroundTasks
from service.api.response import OBResponse
from service.api import response_utils
from service.handler import handler_utils

router = APIRouter()


@router.post("/processes/suicide",
             response_model=OBResponse,
             description='exit process',
             operation_id='exitProcess',
             tags=['Common'])
async def suicide(backgroundtasks: BackgroundTasks):
    handler = handler_utils.new_common_handler()
    backgroundtasks.add_task(handler.suicide)
    return response_utils.new_ok_response("suicide")


@router.post("/connect/keep_alive",
             response_model=OBResponse,
             description='validate or set keep alive token',
             operation_id='validateOrSetKeepAliveToken',
             tags=['Common'])
async def keep_alive(token: str = Query(None, description='token'),
                     overwrite: bool = Query(False, description='force set token when conflict'),
                     is_clear: bool = Query(False, description='is need clear token')):
    handler = handler_utils.new_common_handler()
    return response_utils.new_ok_response(handler.keep_alive(token, overwrite, is_clear))


@router.get("/keys/rsa/public",
            response_model=OBResponse,
            description='rsa public key',
            operation_id='rsaPublicKey',
            tags=['Common'])
async def public_key():
    handler = handler_utils.new_rsa_handler()
    key, err = handler.public_key_to_bytes()
    if err:
        return response_utils.new_internal_server_error_exception(Exception('get rea public key is failed'))
    return response_utils.new_ok_response(key)
