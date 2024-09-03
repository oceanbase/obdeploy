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

import asyncio
from datetime import timedelta

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette_prometheus import metrics, PrometheusMiddleware

from asgi_correlation_id import CorrelationIdMiddleware

from service.common import log
from service.common.core import CoreManager
from service.api.v1 import components, deployments, common, service_info, mirror
from service.middleware.request_response_log import RequestResponseLogMiddleware
from service.middleware.process_time import ProcessTimeMiddleware
from service.middleware.ip_white import IPBlockMiddleware
from service.middleware.idle_shutdown import IdleShutdownMiddleware
from service.handler import handler_utils
from service.api.v1 import ocp_deployments
from service.api.v1 import metadb
from service.api.v1 import installer
from service.api.v1 import component_change
from const import DISABLE_SWAGGER


if DISABLE_SWAGGER == '<DISABLE_SWAGGER>':
    app = FastAPI()
else:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, swagger_ui_oauth2_redirect_url=None)
IDLE_TIME_BEFORE_SHUTDOWN = timedelta(minutes=30)


class OBDWeb(object):

    def __init__(self, obd, white_ip_list=None, resource_path="./"):
        CoreManager.INSTANCE = obd
        self.app = app
        self.app.add_route("/metrics", metrics)
        self.app.include_router(components.router, prefix='/api/v1')
        self.app.include_router(deployments.router, prefix='/api/v1')
        self.app.include_router(common.router, prefix='/api/v1')
        self.app.include_router(service_info.router, prefix='/api/v1')
        self.app.include_router(mirror.router, prefix='/api/v1')
        self.app.include_router(ocp_deployments.router, prefix='/api/v1')
        self.app.include_router(metadb.router, prefix='/api/v1')
        self.app.include_router(installer.router, prefix='/api/v1')
        self.app.include_router(component_change.router, prefix='/api/v1')
        self.app.add_middleware(IdleShutdownMiddleware, logger=log.get_logger(), idle_time_before_shutdown=IDLE_TIME_BEFORE_SHUTDOWN)
        self.app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
        self.app.add_middleware(IPBlockMiddleware, ips=white_ip_list)
        self.app.add_middleware(ProcessTimeMiddleware)
        self.app.add_middleware(RequestResponseLogMiddleware, logger=log.get_logger())
        self.app.add_middleware(PrometheusMiddleware)
        self.app.add_middleware(CorrelationIdMiddleware)
        self.app.add_middleware(GZipMiddleware, minimum_size=1024)
        self.app.mount("/", StaticFiles(directory="{0}/web/dist".format(resource_path), html=True), name="dist")


    @staticmethod
    async def init_mirrors():
        handler = handler_utils.new_mirror_handler()
        await handler.init_mirrors_info()

    @staticmethod
    @app.on_event("startup")
    async def startup_event() -> None:
        asyncio.create_task(OBDWeb.init_mirrors())

    def start(self, port=8680):
        uvicorn.run(self.app, host='0.0.0.0', port=port, log_level="debug", reload=False, log_config=log.get_logger_config(file_name="{0}/{1}".format(CoreManager.INSTANCE.home_path, "app.log")))

