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

