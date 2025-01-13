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

from tool import set_plugin_context_variables


def restart_pre(plugin_context, *args, **kwargs):
    new_clients = kwargs.get('new_clients')
    new_deploy_config = kwargs.get('new_deploy_config')
    variables_dict = {
        "clients": plugin_context.clients,
        "dir_list": ['home_path', 'data_dir'],
        "finally_plugins": ['connect', 'display'],
        "need_bootstrap": False,
        "new_clients": new_clients,
        "new_deploy_config": new_deploy_config,
        "is_restart": True
    }
    set_plugin_context_variables(plugin_context, variables_dict)
    return plugin_context.return_true()



