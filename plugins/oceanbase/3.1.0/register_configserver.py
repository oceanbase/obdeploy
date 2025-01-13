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
    cfg_url = plugin_context.get_variable('cfg_url')

    if not cfg_url or 'ob-configserver' not in added_components:
        stdio.error('Failed to register obconfig_url')
        return plugin_context.return_false()

    for comp in ["oceanbase-ce", "oceanbase"]:
        if comp in added_components:
            stdio.error('Failed to register obconfig_url')
            return plugin_context.return_false()

    cursor = plugin_context.get_return('connect').get_return('cursor')
    try:
        cursor.execute("alter system set obconfig_url = '%s'" % cfg_url)
        cursor.execute("alter system reload server")
    except:
        stdio.error('Failed to register obconfig_url')
        return plugin_context.return_false()

    stdio.stop_loading('succeed')
    return plugin_context.return_true()


