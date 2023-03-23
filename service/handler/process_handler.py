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
