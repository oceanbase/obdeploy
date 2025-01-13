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

import os
import time

from singleton_decorator import singleton

from service.common import log, const
from service.handler.base_handler import BaseHandler

@singleton
class ProcessHandler(BaseHandler):

    def suicide(self):
        pid = os.getpid()
        log.get_logger().info("got suicide requrest, pid is %d", pid)
        time.sleep(const.GRACEFUL_TIMEOUT)
        log.get_logger().info("suicide")
        os.kill(pid, 9)
