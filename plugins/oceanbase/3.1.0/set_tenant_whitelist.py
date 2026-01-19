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

import const
from tool import get_option


def set_tenant_whitelist(plugin_context, create_tenant_options=[], cursor=None, scale_out_component='', *args, **kwargs):
    stdio = plugin_context.stdio
    
    cursor = plugin_context.get_return('connect', spacename='oceanbase-ce').get_return('cursor') if not cursor else cursor
    if not cursor:
        stdio.error('Failed to get database cursor')
        return plugin_context.return_false()
    
    tenant_whitelist = plugin_context.get_variable('tenant_whitelist', default={})
    
    if not tenant_whitelist:
        stdio.verbose('No tenant whitelist to set')
        return plugin_context.return_true()
    
    stdio.start_loading('Set tenant whitelist')
    for tenant_name, whitelist_value in tenant_whitelist.items():
        sql = "ALTER TENANT {} VARIABLES ob_tcp_invited_nodes ='{}'".format(tenant_name, whitelist_value)
        ret = cursor.execute(sql, raise_exception=True, stdio=stdio)
        if ret is False:
            stdio.error('Failed to set whitelist for tenant: {}'.format(tenant_name))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    
    stdio.stop_loading('succeed')
    return plugin_context.return_true()

