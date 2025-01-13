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

from tool import Cursor


def register_configserver(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    stdio = plugin_context.stdio
    stdio.start_loading('%s register ob-configserver' % cluster_config.name)
    obproxy_config_server_url = plugin_context.get_variable('obproxy_config_server_url')

    if not obproxy_config_server_url or 'ob-configserver' not in added_components:
        stdio.error('Failed to register obproxy_config_server_url')
        return plugin_context.return_false()

    for comp in ["obproxy-ce", "obproxy"]:
        if comp in added_components:
            stdio.error('Failed to register obproxy_config_server_url')
            return plugin_context.return_false()

    cursors = plugin_context.get_return('connect').get_return('cursor')
    for server in cluster_config.servers:
        try:
            cursors[server].execute("alter proxyconfig set obproxy_config_server_url='%s'" % obproxy_config_server_url)
        except:
            stdio.error('Failed to register obproxy_config_server_url')
            return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true(need_restart=True)


