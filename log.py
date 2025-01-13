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

from __future__ import absolute_import, division, print_function


import logging
from logging import handlers


class Logger(logging.Logger):

    def __init__(self, name, level=logging.DEBUG):
        super(Logger, self).__init__(name, level)
        self.buffer = []
        self.buffer_size = 0

    def _log(self, level, msg, args, end='\n', **kwargs):
        return super(Logger, self)._log(level, msg, args, **kwargs)