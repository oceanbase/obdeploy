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

from singleton_decorator import singleton

from _stdio import BufferIO


@singleton
class CoreManager(object):

    INSTANCE = None

    def __init__(self):
        if CoreManager.INSTANCE is None:
            raise Exception('CoreManager Uninitialized')
        self._buffer = BufferIO(False)
        CoreManager.INSTANCE.stdio.set_output_stream(self._buffer)
        CoreManager.INSTANCE.stdio.set_input_stream(BufferIO(False))
        self._obd = CoreManager.INSTANCE
        self._context = defaultdict(lambda: defaultdict(lambda: None))

    def get_obd(self):
        return self._obd

    def get_buffer(self):
        return self._buffer

    def get_context(self):
        return self._context


