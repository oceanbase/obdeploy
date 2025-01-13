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

import os


def bootstrap(plugin_context, start_env=None, *args, **kwargs):
    if not start_env:
        raise Exception("start env is needed")
    clients = plugin_context.clients
    for server in start_env:
        client = clients[server]
        server_config = start_env[server]
        bootstrap_flag = os.path.join(server_config['home_path'], '.bootstrapped')
        client.execute_command('touch %s' % bootstrap_flag)
    return plugin_context.return_true()

