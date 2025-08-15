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

import getpass
import re

from ssh import SshClient, SshConfig, create_sudo_privileges_client
from tool import get_option, get_sudo_prefix


def sshclient(host=None, username=None, password=None, stdio=None):
    client = SshClient(
        SshConfig(
            host,
            username,
            password,
        ),
        stdio
    )
    if not client.connect(stdio_func='verbose'):
        return None
    return client


def get_client(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options

    password = get_option(options, 'password')
    ip = get_option(options, 'host', '127.0.0.1')
    username = get_option(options, 'username', 'admin')

    stdio.print('Connecting to the server')
    if not re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
        stdio.error('Invalid IP address format. Please enter a valid IP address.')
        return plugin_context.return_false()

    sudo_client = None
    need_init_user = True
    client = sshclient(ip, username, password, stdio)
    if client:
        sudo_prefix = get_sudo_prefix(client)
        if client.execute_command(sudo_prefix + 'whoami'):
            sudo_client = client
            need_init_user = False
    elif ip in ['127.0.0.1', 'localhost', '127.1', '127.0.1']:
        client = sshclient(host=ip, username=getpass.getuser(), stdio=stdio)
        sudo_prefix = get_sudo_prefix(client)
        if client and client.execute_command(sudo_prefix + 'whoami'):
            sudo_client = client

    if not sudo_client:
        sudo_client = create_sudo_privileges_client(stdio, 'verbose', ip,  "'%s: Failed to verify sudo with password." % ip, port=22)
        if not sudo_client:
            stdio.error("'%s: Failed to verify sudo with password." % ip)
            return plugin_context.return_false()

    plugin_context.set_variable('sudo_client', sudo_client)
    plugin_context.set_variable('need_init_user', need_init_user)
    plugin_context.set_variable('sshclient_func', sshclient)
    return plugin_context.return_true()
