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
from service.common import core

SPACENAME = "API"


class BaseHandler(object):
    def __init__(self):
        self._obd = core.CoreManager().get_obd()
        self._buffer = core.CoreManager().get_buffer()
        self._context = core.CoreManager().get_context()

    @property
    def obd(self):
        return self._obd

    @property
    def buffer(self):
        return self._buffer

    @property
    def context(self):
        return self._context
