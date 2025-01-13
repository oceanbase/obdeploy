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

from typing import List

from fastapi import Body
from pydantic import BaseModel


class ComponentInfo(BaseModel):
    estimated_size: int = Body(0, description='estimated size after install')
    version: str = Body('', description='component version')
    type: str = Body('local', description='component type,ex:remote,local')
    release: str = Body('', description='component release no')
    arch: str = Body('', description='component package arch info')
    md5: str = Body('', description='component package md5 info')
    version_type: str = Body('', description=' version type,ex:ce,business')


class Component(BaseModel):
    name: str = Body(..., description='component name')
    info: List[ComponentInfo] = Body(None, description='info')


class ConfigParameter(BaseModel):
    is_essential: bool = Body(False, description='is essential')
    name: str = Body("", description='parameter name')
    require: bool = Body(False, description='parameter is it required')
    auto: bool = Body(False, description='parameter can be calculated automatically')
    description: str = Body("", description='parameter description')
    type: str = Body("", description='parameter type')
    default: str = Body("", description='parameter default value')
    min_value: str = Body("", description='parameter min value')
    max_value: str = Body("", description='parameter max value')
    need_redeploy: bool = Body(False, description='need redeploy')
    modify_limit: str = Body("", description='modify limit')
    need_reload: bool = Body(False, description='need reload')
    need_restart: bool = Body(False, description='need restart')
    section: str = Body("", description='section')


class ParameterMeta(BaseModel):
    component: str = ...
    version: str = ...
    config_parameters: List[ConfigParameter] = ...


class ParameterFilter(BaseModel):
    component: str = Body(..., description='component name')
    version: str = Body(..., description='version name')
    is_essential_only: bool = Body(False, description='essential parameter filter')


class ParameterRequest(BaseModel):
    filters: List[ParameterFilter] = Body(..., description='parameter filters')

