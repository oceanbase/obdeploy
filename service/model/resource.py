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

