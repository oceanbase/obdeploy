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

from fastapi import Body
from pydantic import BaseModel
from typing import List


class ServiceInfo(BaseModel):
    user: str = Body(..., description='user name')


class DeployName(BaseModel):
    name: str = Body('', description="deploy name list")
    deploy_user: str = Body('', description="deploy user")
    ob_servers: List[str] = Body([], description="ob servers")
    ob_version: str = Body('', description="ob version")
    create_date: str = Body(None, description="ob create date")


class DeployNames(BaseModel):
    name: List[str] = Body([], description="deploy name list")
