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
