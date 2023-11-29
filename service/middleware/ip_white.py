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