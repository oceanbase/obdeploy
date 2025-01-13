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
from typing import Optional

from fastapi import APIRouter, Path, Header

from service.api.response import OBResponse, DataList

from service.model.components import Component, ComponentInfo, ParameterMeta, ParameterRequest, ParameterFilter

import service.api.response_utils as response_utils
import service.handler.handler_utils as handler_utils
from service.common import log

router = APIRouter()


@router.post("/components/parameters",
            response_model=OBResponse[DataList[ParameterMeta]],
            description='query component parameters',
            operation_id='queryComponentParameters',
            tags=['Components'])
async def list_component_parameters(parameter_request: ParameterRequest = ..., accept_language: Optional[str] = Header(None),):
    handler = handler_utils.new_component_handler()
    parameters = handler.list_component_parameters(parameter_request, accept_language)
    return response_utils.new_ok_response(parameters)


@router.get("/components/{component}",
            response_model=OBResponse[Component],
            description='query component by component name',
            tags=['Components'],
            operation_id='queryComponentByComponentName')
async def get_component(component: str = Path(description='component name')):
    handler = handler_utils.new_component_handler()
    try:
        ret = handler.get_component(component)
        if ret is None:
            return response_utils.new_not_found_exception(Exception("component {0} not found".format(component)))
        else:
            return response_utils.new_ok_response(ret)
    except Exception as ex:
        return response_utils.new_service_unavailable_exception(ex)


@router.get("/components",
            response_model=OBResponse[DataList[Component]],
            description='query all component versions',
            operation_id='queryAllComponentVersions',
            tags=['Components'])
async def list_components():
    handler = handler_utils.new_component_handler()
    try:
        components = handler.list_components()
        return response_utils.new_ok_response(components)
    except Exception as ex:
        return response_utils.new_service_unavailable_exception(ex)


