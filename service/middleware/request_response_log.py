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
