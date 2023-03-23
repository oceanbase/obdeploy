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

from collections import defaultdict

from _plugin import PluginContextNamespace
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
