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


class SshAuthMethod(StrEnum):
    PUBKEY = auto()
    PASSWORD = auto()


class SshAuth(BaseModel):
    user: str = Body("", description="username")
    auth_method: SshAuthMethod = Body(SshAuthMethod.PASSWORD, description="auth method")
    password: str = Body("", description="password")
    private_key: str = Body("", description="private key")
    port: int = Body(0, description="ssh port")


