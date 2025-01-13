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
from enum import auto
from fastapi_utils.enums import StrEnum
from fastapi import Body
from pydantic import BaseModel


class TaskStatus(StrEnum):
    RUNNING = auto()
    FINISHED = auto()


class TaskResult(StrEnum):
    SUCCESSFUL=auto()
    FAILED=auto()
    RUNNING=auto()


class PrecheckEventResult(StrEnum):
    PASSED = auto()
    FAILED = auto()
    RUNNING = auto()


class TaskStepInfo(BaseModel):
    name: str = Body('', description="task step")
    status: TaskStatus = Body('', description="task step status")
    result: TaskResult = Body('', description="task step result")


class TaskInfo(BaseModel):
    id: int = Body(..., description="task id")
    status: TaskStatus = Body(..., description="task status")
    result: TaskResult = Body(..., description="task result")
    total: str = Body('port, mem, disk, ulimit, aio, net, ntp, dir, param, ssh', description="total steps")
    finished: str = Body('', description="finished steps")
    current: str = Body('', description="current step")
    message: str = Body('', description="task message")
    info: List[TaskStepInfo] = Body([], description="")


class PreCheckResult(BaseModel):
    name: str = Body(..., description="precheck event name")
    server: str = Body("", description="precheck server")
    result: PrecheckEventResult = Body('', description="precheck event result")
    recoverable: bool = Body(False, description="precheck event recoverable")
    code: str = Body('', description="error code")
    description: str = Body('', description='error description')
    advisement: str = Body("", description="advisement of precheck event failure")


class PrecheckTaskInfo(BaseModel):
    task_info: TaskInfo = Body('', description="task detailed info")
    precheck_result: List[PreCheckResult] = Body([], description="precheck result")


class TaskLog(BaseModel):
    log: str = Body("", description="task log content")
    offset: int = Body(0, description="offset of current log")
