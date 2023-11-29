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


class DiskInfo(BaseModel):
    dev: str = Body(..., description="dev")
    mount_path: str = Body(..., description="mount path")
    total_size: str = Body(..., description="total size")
    free_size: str = Body(..., description="free size")


class ServerResource(BaseModel):
    address: str = Body(..., description="server address")
    cpu_total: float = Body(..., description="total cpu")
    cpu_free: float = Body(..., description="free cpu")
    memory_total: str = Body(..., description="total memory size")
    memory_free: str = Body(..., description="free memory size")
    disk: List[DiskInfo] = Body(..., description="disk info")


class Disk(BaseModel):
    path: str = Body(..., description="path")
    disk_info: DiskInfo = Body(..., description="disk info")


class MetaDBResource(BaseModel):
    address: str = Body(..., description="server address")
    disk: List[Disk] = Body(..., description="path: disk_info")
    memory_limit_lower_limit: int = Body(..., description="memory_limit lower limit")
    memory_limit_higher_limit: int = Body(..., description="memory_limit higher limit")
    memory_limit_default: int = Body(..., description="default memory_limit")
    data_size_default: int = Body(..., description="default data size")
    log_size_default: int = Body(..., description="default log size")
    flag: int = Body(..., description="which solution to use")


class ResourceCheckResult(BaseModel):
    address: str = Body(..., description='server ip')
    name: str = Body(..., description="resource check type name, eq memory_limit, data_dir, home_path, log_dir..")
    check_result: bool = Body(True, description="check result, true/false")
    error_message: List[str] = Body([], description='error message, eq path not enough')

