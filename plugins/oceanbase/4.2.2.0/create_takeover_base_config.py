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

from tool import OrderedDict


def create_takeover_base_config(plugin_context, *args, **kwargs):
    options = plugin_context.options
    host = getattr(options, 'host')
    mysql_port = getattr(options, 'mysql_port')
    root_password = getattr(options, 'root_password')

    config = OrderedDict()
    component_name = 'oceanbase-ce'
    global_config = {
        'mysql_port': mysql_port,
        'root_password': root_password
    }
    config[component_name] = {
        'servers': [host],
        'global': global_config
    }

    user_config = {}
    ssh_key_map = {
        'username': 'ssh_user',
        'ssh_password': 'password',
        'key_file': 'ssh_key_file',
        'port': 'ssh_port'
    }
    for key in ssh_key_map:
        opt = ssh_key_map[key]
        val = getattr(options, opt)
        if val is not None:
            user_config[key] = val
    if user_config:
        config['user'] = user_config
    
    return plugin_context.return_true('takeover_config', config)