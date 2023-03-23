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

from fastapi import APIRouter


from service.api import response_utils
from service.api.response import OBResponse, DataList
from service.handler import handler_utils
from service.model.mirror import Mirror

router = APIRouter()


@router.get("/mirrors",
            response_model=OBResponse[DataList[Mirror]],
            description='list remote mirrors',
            operation_id='listRemoteMirrors',
            tags=['Mirror'])
async def get_effective_mirror():
    handler = handler_utils.new_mirror_handler()
    try:
        mirrors = handler.list_mirrors()
    except Exception as e:
        return response_utils.new_service_unavailable_exception(e)
    return response_utils.new_ok_response(mirrors)
