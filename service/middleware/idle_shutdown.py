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

import os
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
import asyncio


class IdleShutdownMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger, idle_time_before_shutdown: timedelta):
        super().__init__(app)
        self.idle_time_before_shutdown = idle_time_before_shutdown
        self.last_request_time = datetime.utcnow()
        self.logger = logger
        self.background_task_started = False
        self.background_task = None

    async def dispatch(self, request, call_next):
        self.logger.info("dispatch request and update last request time")
        self.last_request_time = datetime.utcnow()
        if not self.background_task_started:
            self.background_task = asyncio.create_task(self.check_for_idle())
            self.background_task_started = True
        response = await call_next(request)
        return response

    async def check_for_idle(self):
        while True:
            await asyncio.sleep(1)  # Sleep for 60 seconds before the next check
            if datetime.utcnow() - self.last_request_time > self.idle_time_before_shutdown:
                self.logger.info("Shutting down due to inactivity.")
                pid = os.getpid()
                self.logger.info("shutdown pid %d", pid)
                os.kill(pid, 9)
                break
