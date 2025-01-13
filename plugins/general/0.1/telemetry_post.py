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

import json
import requests

from const import TELEMETRY_URL, TELEMETRY_COMPONENT, TELEMETRY_SIG
from tool import timeout


def telemetry_post(plugin_context, telemetry_post_data={}, *args, **kwargs):
    stdio = plugin_context.stdio
    if telemetry_post_data:
        data = json.dumps(telemetry_post_data, indent=4)
        stdio.verbose('post data: %s' % data)
        try:
            with timeout(30):
                requests.post(url=TELEMETRY_URL, \
                    data=json.dumps({'component': TELEMETRY_COMPONENT, 'content': data}), \
                    headers={'sig': TELEMETRY_SIG, 'Content-Type': 'application/json'})
            return plugin_context.return_true()
        except:
            stdio.exception('post data failed')
            return plugin_context.return_false()
    else:
        stdio.verbose('noting to post')
        return plugin_context.return_false()