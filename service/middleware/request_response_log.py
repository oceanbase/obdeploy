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

import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import iterate_in_threadpool


async def set_body(request, body):
    async def receive():
        return {'type': 'http.request', 'body': body}
    request._receive = receive

class RequestResponseLogMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            logger, ):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request, call_next):
        request_body = await request.body()
        self.logger.info("app receive request, method: %s, url: %s, query_params: %s, body: %s, from: %s:%d", request.method, request.url, request.query_params, request_body.decode(), request.client.host, request.client.port)
        await set_body(request, request_body)
        response = await call_next(request)
        self.logger.info("app send response, code: %d", response.status_code)
        return response
