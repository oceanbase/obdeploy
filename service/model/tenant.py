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

