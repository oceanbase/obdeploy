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

import re

import _errno as err


def password_check(password):
    if not re.match(r'^[\w~^*{}\[\]_\-+]+$', password):
        return False
    return True


def http_basic_auth_password_check(plugin_context, start_check_status, **kwargs):
    critical = plugin_context.get_variable('check_fail')
    env = plugin_context.get_variable('start_env')
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.verbose('http_basic_auth_password check')

    for server in cluster_config.servers:
        server_config = env[server]

        # http_basic_auth_password check
        http_basic_auth_password = server_config.get('http_basic_auth_password')
        if http_basic_auth_password:
            if not password_check(http_basic_auth_password):
                critical(server, 'password', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='obagent', key='http_basic_auth_password', rule='^[\w~^*{}\[\]_\-+]+$'), suggests=[err.SUG_OBAGENT_EDIT_HTTP_BASIC_AUTH_PASSWORD.format()])
    return plugin_context.return_true()