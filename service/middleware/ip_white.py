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
import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.exceptions import HTTPException


class IPBlockMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, ips):
        self.app = app
        self.ip_whitelist = ips
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        remote_ip = request.client.host
        if self.ip_whitelist:
            for ip_regx in self.ip_whitelist:
                if re.match(ip_regx, remote_ip):
                    break
            else:
                raise HTTPException(status_code=403, detail="Forbidden IP")
        response = await call_next(request)
        return response