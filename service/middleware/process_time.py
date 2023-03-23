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

import time
from starlette.middleware.base import BaseHTTPMiddleware

class ProcessTimeMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            ):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        end_time = time.time()
        process_time_str = "{0}ms".format((end_time - start_time) * 1000)
        response.headers["X-Process-Time"] = process_time_str
        return response
