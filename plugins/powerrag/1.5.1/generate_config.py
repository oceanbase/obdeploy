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
from tool import ConfigUtil


def generate_config(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    global_config = cluster_config.get_original_global_conf()
    stdio.start_loading('Generate powerrag config')

    ob_config = None
    for comp in const.COMPS_OB:
        if comp in cluster_config.depends:
            ob_servers = cluster_config.get_depend_servers(comp)
            ob_config = cluster_config.get_depend_config(comp, ob_servers[0])
    if not ob_config:
        stdio.error('can not find oceanbase config')
        return plugin_context.return_false()

    powerrag_root_password = ob_config.get('ob_tenant_password') or None
    if 'ob_tenant_password' not in global_config and not powerrag_root_password:
        cluster_config.update_global_conf('ob_tenant_password', ConfigUtil.get_random_pwd_by_total_length(), False)
    if 'default_password' not in global_config:
        cluster_config.update_global_conf('default_password', ConfigUtil.get_random_pwd_by_total_length(), False)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()

