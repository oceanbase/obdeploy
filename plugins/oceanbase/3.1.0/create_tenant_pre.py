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

import re
from tool import get_option

def create_tenant_pre(plugin_context,  *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    tenant_name = get_option(options, 'tenant_name', 'test')
    if len(tenant_name) > 63:
        stdio.error('tenant name must be less than 64 characters')
        return plugin_context.return_false()
    pattern = r'^[A-Za-z_][\w]*$'
    if not re.match(pattern, tenant_name):
        stdio.error('tenant name must start with a letter or underscore, and can only contain letters, numbers and underscores')
        return plugin_context.return_false()
    return plugin_context.return_true()

