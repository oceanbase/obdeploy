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

def dump_standbyro_password(plugin_context, *args, **kwargs):
    cmds = plugin_context.cmds
    if kwargs.get('option_mode') == 'log_source':
        tenant_name = cmds[1]
    cluster_config = plugin_context.cluster_config
    if kwargs.get("dump_cluster"):
        cluster_config = kwargs.get("dump_cluster")
    if kwargs.get('dump_tenant'):
        tenant_name = kwargs.get('dump_tenant')

    standbyro_password = plugin_context.get_variable('standbyro_password')
    standbyro_password_dict = cluster_config.get_component_attr('standbyro_password')
    if standbyro_password_dict:
        standbyro_password_dict[tenant_name] = standbyro_password
    else:
        standbyro_password_dict = {tenant_name: standbyro_password}
    cluster_config.update_component_attr('standbyro_password', standbyro_password_dict, save=True)

    return plugin_context.return_true()