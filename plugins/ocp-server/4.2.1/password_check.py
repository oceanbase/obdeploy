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
import re

import _errno as err
from _deploy import DeployStatus


def password_regular_check(passwd):
    pattern = r"((?=(.*\d){2,})(?=(.*[a-z]){2,})(?=(.*[A-Z]){2,})(?=(.*[~!@#%^&*_\-+=|(){}\[\]:;,.?/]){2,})[0-9a-zA-Z~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32})"
    if re.match(pattern, passwd):
        return True


def password_check(plugin_context, **kwargs):
    check_pass = plugin_context.get_variable('check_pass')
    error = plugin_context.get_variable('error')
    env = plugin_context.get_variable('start_env')

    cluster_config = plugin_context.cluster_config
    deploy_status = plugin_context.deploy_status
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    options = plugin_context.options

    server_config = env[cluster_config.servers[0]]
    client = clients[cluster_config.servers[0]]
    # admin_passwd check
    bootstrap_flag = os.path.join(server_config['home_path'], '.bootstrapped')
    stdio.verbose('admin_password check')
    if deploy_status == DeployStatus.STATUS_DEPLOYED and not client.execute_command('ls %s' % bootstrap_flag) and not getattr(options, 'skip_password_check', False):
        for server in cluster_config.servers:
            server_config = env[server]
            admin_passwd = server_config['admin_password']
            if not admin_passwd or not password_regular_check(admin_passwd):
                error(server, 'admin_password', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='ocp', key='admin_password', rule='Must be 8 to 32 characters in length, and must contain at least two digits, two uppercase letters, two lowercase letters, and two of the following special characters:~!@#%^&*_-+=|(){{}}[]:;,.?/)'), suggests=[err.SUG_OCP_EXPRESS_EDIT_ADMIN_PASSWD.format()])
                continue
            check_pass(server, 'admin_password')
    return plugin_context.return_true()