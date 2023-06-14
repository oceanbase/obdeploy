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


from __future__ import absolute_import, division, print_function

import json
import requests

from const import TELEMETRY_URL
from tool import timeout


def telemetry_post(plugin_context, telemetry_post_data={}, *args, **kwargs):
    stdio = plugin_context.stdio
    if telemetry_post_data:
        data = json.dumps(telemetry_post_data, indent=4)
        stdio.verbose('post data: %s' % data)
        try:
            with timeout(30):
                requests.post(url=TELEMETRY_URL, data=json.dumps({'content': data}), headers={'sig': 'dbe97393a695335d67de91dd4049ba', 'Content-Type': 'application/json'})
            return plugin_context.return_true()
        except:
            stdio.exception('post data failed')
            return plugin_context.return_false()
    else:
        stdio.verbose('noting to post')
        return plugin_context.return_false()