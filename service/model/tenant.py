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
from typing import List, Optional
from enum import auto
from fastapi import Body
from fastapi_utils.enums import StrEnum
from pydantic import BaseModel


# only support cpu and memory currently
class TenantResource(BaseModel):
    cpu: float = Body(2, description="cpu resource of a tenant")
    memory: int = Body(4, description="memory resource of a tenant in GB")


class TenantUser(BaseModel):
    tenant_name: str = Body(..., description="tenant name")
    user_name: str = Body('root', description="user name")
    user_database: str = Body('', description='user database')


class TenantConfig(BaseModel):
    name: TenantUser = Body(..., description="tenant name")
    password: Optional[str] = Body('', description="tenant password")
    resource: Optional[TenantResource] = Body(TenantResource(), description="tenant resource")

