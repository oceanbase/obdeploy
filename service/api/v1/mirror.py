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


from service.api import response_utils
from service.api.response import OBResponse, DataList
from service.handler import handler_utils
from service.model.mirror import Mirror

router = APIRouter()


@router.get("/mirrors",
            response_model=OBResponse[DataList[Mirror]],
            description='list remote mirrors',
            operation_id='listRemoteMirrors',
            tags=['Mirror'])
async def get_effective_mirror():
    handler = handler_utils.new_mirror_handler()
    try:
        mirrors = handler.list_mirrors()
    except Exception as e:
        return response_utils.new_service_unavailable_exception(e)
    return response_utils.new_ok_response(mirrors)
