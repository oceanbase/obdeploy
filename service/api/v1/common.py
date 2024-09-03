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
