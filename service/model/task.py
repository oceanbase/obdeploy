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
