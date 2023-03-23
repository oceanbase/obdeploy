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

from fastapi import APIRouter

from fastapi import BackgroundTasks
from service.api.response import OBResponse
from service.api import response_utils
from service.handler import handler_utils

router = APIRouter()


@router.post("/processes/suicide",
             response_model=OBResponse,
             description='exit process',
             operation_id='exitProcess',
             tags=['Processes'])
async def suicide(backgroundtasks: BackgroundTasks):
    handler = handler_utils.new_process_handler()
    backgroundtasks.add_task(handler.suicide)
    return response_utils.new_ok_response("suicide")
