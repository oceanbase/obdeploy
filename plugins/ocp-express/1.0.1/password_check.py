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


def password_regular_check(passwd):
    pattern = r'''^(?=(.*[a-z]){2,})(?=(.*[A-Z]){2,})(?=(.*\d){2,})(?=(.*[~!@#%^&*_\-+=|(){}\[\]:;,.?/]){2,})[A-Za-z\d~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32}$'''
    return True if re.match(pattern, passwd) else False


def password_check(plugin_context, **kwargs):
    error = plugin_context.get_variable('error')
    env = plugin_context.get_variable('start_env')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.verbose('admin_password check')
    # admin_passwd check
    for server in cluster_config.servers:
        server_config = env[server]
        admin_passwd = server_config.get('admin_passwd')
        if not admin_passwd or not password_regular_check(admin_passwd):
            error(server, 'admin_passwd', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='ocp-express', key='admin_passwd', rule='The password must be 8 to 32 characters in length, containing at least 2 uppercase letters, 2 lowercase letters, 2 numbers, and 2 of the following special characters: ~!@#%^&*_-+=|(){{}}[]:;,.?/'), suggests=[err.SUG_OCP_EXPRESS_EDIT_ADMIN_PASSWD.format()])
    return plugin_context.return_true()