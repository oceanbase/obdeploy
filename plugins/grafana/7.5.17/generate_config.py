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

from tool import ConfigUtil


def generate_config(plugin_context, auto_depend=False, generate_check=True, return_generate_keys=False, only_generate_password=False, *args, **kwargs):
    if return_generate_keys:
        generate_keys = ['login_password']
        return plugin_context.return_true(generate_keys=generate_keys)

    cluster_config = plugin_context.cluster_config
    generate_random_password(cluster_config)
    if only_generate_password:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    success = True
    have_depend = False
    depend = 'prometheus'
    generate_configs = {'global': {}}
    plugin_context.set_variable('generate_configs', generate_configs)
    stdio.start_loading('Generate grafana configuration')

    global_config = cluster_config.get_original_global_conf()
    login_password = global_config.get('login_password')
    if login_password:
        if generate_check:
            login_password = str(login_password)
            if len(login_password) < 5:
                stdio.error("Grafana : the length of configuration 'login_password' cannot be less than 5")
                success = False
            elif login_password == "admin":
                stdio.error("Grafana : configuration 'login_password' in configuration file should not be 'admin'")
                success = False

    if not success:
        stdio.stop_loading('fail')
        return 

    for comp in cluster_config.depends:
        if comp == depend:
            have_depend = True

    if not have_depend and auto_depend:
        cluster_config.add_depend_component(depend)

    stdio.stop_loading('succeed')
    return plugin_context.return_true()


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'login_password' not in global_config:
        cluster_config.update_global_conf('login_password', ConfigUtil.get_random_pwd_by_total_length(), False)