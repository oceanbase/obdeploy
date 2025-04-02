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


def generate_random_password(cluster_config):
    add_components = cluster_config.get_deploy_added_components()
    global_config = cluster_config.get_original_global_conf()
    if cluster_config.name in add_components and 'admin_passwd' not in global_config:
        cluster_config.update_global_conf('admin_passwd', ConfigUtil.get_random_pwd_by_rule(), False)


def generate_config_pre(plugin_context, *args, **kwargs):
    generate_keys = ['admin_passwd']
    plugin_context.set_variable('generate_keys', generate_keys)
    plugin_context.set_variable('generate_random_password', generate_random_password)
    return plugin_context.return_true()