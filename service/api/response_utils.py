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
