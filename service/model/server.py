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

from fastapi import Body
from fastapi_utils.enums import StrEnum
from typing import List, Optional
from pydantic import BaseModel
from enum import auto

from service.model.metadb import DatabaseConnection


class InstallerMode(StrEnum):
    STANDARD = auto()
    COMPACT = auto()


class ComponentInfo(BaseModel):
    name: str = Body("ocp-server", description="ocp component")
    ip: List[str] = Body([], description="server address")


class OcpServerInfo(BaseModel):
    user: str = Body('', description="deploy user")
    ocp_version: str = Body('', description="ocp-server current version")
    component: List[ComponentInfo] = Body([], description="component info")
    tips: bool = Body(False, description='display tips')
    msg: str = Body('', description="failed message")


class MsgInfo(BaseModel):
    msg: str = Body(..., description="failed message")
    status: int = Body(..., description='eq: 0, 1')


class UserInfo(BaseModel):
    username: str = Body(..., description='system user')


