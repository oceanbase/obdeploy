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


