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
