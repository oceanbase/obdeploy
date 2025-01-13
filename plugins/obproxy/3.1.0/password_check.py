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

import _errno as err


def password_check(plugin_context, *args, **kwargs):
    alert = plugin_context.get_variable('alert')
    check_pass = plugin_context.get_variable('check_pass')
    cluster_config = plugin_context.cluster_config

    global_config = cluster_config.get_original_global_conf()
    key = 'observer_sys_password'
    for comp in ["oceanbase", "oceanbase-ce"]:
        if comp in cluster_config.depends:
            if key in global_config:
                alert(cluster_config.servers[0], 'password',
                    err.WC_PARAM_USELESS.format(key=key, current_comp=cluster_config.name, comp=comp),
                    [err.SUG_OB_SYS_PASSWORD.format()]
                )
            break
    for server in cluster_config.servers:
        check_pass(server, 'password')
    return plugin_context.return_true()