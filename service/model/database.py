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


class DatabaseConnection(BaseModel):
    cluster_name: str = Body('', description="cluster name of the connection in installer")
    host: str = Body('', description="host")
    port: int = Body(2881, description="port")
    user: str = Body('meta_user@ocp_meta', description="user")
    password: str = Body('', description="password")
    database: str = Body('meta_database', description="database")

