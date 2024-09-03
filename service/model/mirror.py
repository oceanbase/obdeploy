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
from typing import Union


class Mirror(BaseModel):
    mirror_path: str = Body('', description='mirror path')
    name: str = Body(..., description='mirror name')
    section_name: str = Body('', description='section name')
    baseurl: str = Body('', description='baseurl')
    repomd_age: int = Body(None, description='repomd age')
    repo_age: int = Body(None, description='repo age')
    priority: int = Body(None, description='priority')
    gpgcheck: Union[str, int] = Body('', description='gpgcheck')
    enabled: bool = Body('', description='remote mirror is enabled')
    available: bool = Body('', description='remote mirror is enabled')

