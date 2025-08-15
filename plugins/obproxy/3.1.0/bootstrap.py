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

from const import COMPS_OB

def bootstrap(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    cursor = plugin_context.get_return('connect').get_return('cursor')
    if not cursor:
        stdio.error('obproxy bootstrap need oceanbase')
        return plugin_context.return_false()
    global_ret = True
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        for key in ['observer_sys_password']:
            sql = 'alter proxyconfig set %s = %%s' % key
            for comp in COMPS_OB:
                if comp in cluster_config.depends:
                    ob_servers = cluster_config.get_depend_servers(comp)
                    ob_config = cluster_config.get_depend_config(comp, ob_servers[0])
                    value = ob_config.get('proxyro_password', '')
                    break
                else:
                    value = server_config.get(key, '')
            value = '' if value is None else str(value)
            ret = cursor[server].execute(sql, [value], exc_level="verbose")
            if ret is False:
                stdio.error('failed to set %s for obproxy(%s)' % (key, server))
                global_ret = False
    if global_ret:
        return plugin_context.return_true()
    else:
        return plugin_context.return_false()
