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

import traceback
from service.api.response import OBResponse, DataList
from fastapi import HTTPException
from http import HTTPStatus
from service.common import log


def new_ok_response(data):
    response = OBResponse()
    response.code = HTTPStatus.OK
    response.msg = "successful"
    response.success = True
    if isinstance(data, list):
        data_list = DataList()
        data_list.total = len(data)
        data_list.items = data
        response.data = data_list
    else:
        response.data = data
    return response


def new_bad_request_exception(ex):
    log.get_logger().error("got bad request exception: {0}".format(traceback.format_exc()))
    raise HTTPException(HTTPStatus.BAD_REQUEST, detail="bad request, exception: {0}".format(ex))


def new_not_found_exception(ex):
    log.get_logger().error("got not found exception: {0}".format(traceback.format_exc()))
    raise HTTPException(HTTPStatus.NOT_FOUND, detail="resource not found, exception: {0}".format(ex))


def new_internal_server_error_exception(ex):
    log.get_logger().error("got internal server error exception: {0}".format(traceback.format_exc()))
    log.get_logger().error("Runing Exception: {}".format(ex))
    raise HTTPException(HTTPStatus.INTERNAL_SERVER_ERROR, detail="internal server error, exception: {0}".format(ex))


def new_service_unavailable_exception(ex):
    log.get_logger().error("got service unavailable exception: {0}".format(traceback.format_exc()))
    raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, detail="service unavailable, exception: {0}".format(ex))


def new_not_implemented_exception(ex):
    log.get_logger().error("got not implemented exception: {0}".format(traceback.format_exc()))
    raise HTTPException(HTTPStatus.NOT_IMPLEMENTED, detail="not implemented, exception: {0}".format(ex))
