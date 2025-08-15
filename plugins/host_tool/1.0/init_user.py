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

from _stdio import FormatText
from tool import get_option, set_system_conf, get_sudo_prefix


def create_user(client, username):
    sudo_prefix = get_sudo_prefix(client)
    cmd = f'{sudo_prefix}useradd -U {username} -m -d /home/{username} -s /bin/bash; {sudo_prefix}chown -R {username} /home/{username};'
    if client.execute_command(cmd):
        return True
    return False


def change_owner_if_exists(dir_path, username, client, stdio):
    if not client.execute_command(f'ls {dir_path}'):
        stdio.warn('can`t find dir %s' % dir_path)
    else:
        sudo_prefix = get_sudo_prefix(client)
        client.execute_command(sudo_prefix + 'chown -R %s %s' % (username, dir_path))


def init_user(plugin_context, sudo_client, need_init_user, sshclient_func, *args, **kwargs):
    def get_ulimits(client):
        ret = client.execute_command('bash -c "ulimit -a"')
        src_data = re.findall('\s?([a-zA-Z\s]+[a-zA-Z])\s+\([a-zA-Z\-,\s]+\)\s+([\d[a-zA-Z]+)', ret.stdout) if ret else []
        ulimits = {}
        for key, value in src_data:
            ulimits[key] = value
        return ulimits

    stdio = plugin_context.stdio
    options = plugin_context.options

    password = get_option(options, 'password')
    ip = get_option(options, 'host', '127.0.0.1')
    username = get_option(options, 'username', 'admin')

    if need_init_user and not sudo_client.execute_command('id %s' % username):
        if not password:
            stdio.error('Create %s user failed: password missing, -p parameter is required' % username)
            return plugin_context.return_false()
        stdio.print('Create user %s' % username)
        if not create_user(sudo_client, username):
            stdio.stop_loading('fail')
            stdio.error("'%s: Failed to create user %s." % (ip, username))
            return plugin_context.return_false()

    sudo_prefix = get_sudo_prefix(sudo_client)
    if password:
        stdio.print('Set %s`s password' % username)
        if not sudo_client.execute_command(f'echo "{username + ":" + password}" | {sudo_prefix}chpasswd;'):
            stdio.warn('set user password failed.')


    cmd = sudo_prefix + '-l -U %s' % username
    if not ("NOPASSWD" in sudo_client.execute_command(cmd).stdout):
        stdio.print('Configure passwordless sudo for %s' % username)
        if not sudo_client.execute_command(sudo_prefix + 'echo "%s      ALL=(ALL)       NOPASSWD: ALL" >>/etc/sudoers' % username):
            stdio.stop_loading('fail')
            return plugin_context.return_false()

    stdio.print('Enable password login')
    sudo_client.execute_command(sudo_prefix + "sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config")
    sudo_client.execute_command(sudo_prefix + "sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config")
    sudo_client.execute_command(sudo_prefix + "systemctl restart sshd")

    stdio.print('Modify ulimit parameters')
    ulimits = get_ulimits(sudo_client)
    ulimits_items = {
        'open files': {
            'value': '655350',
            'name': 'nofile'
        },
        'max user processes': {
            'value': '655360',
            'name': 'nproc'
        },
        'core file size': {
            'value': 'unlimited',
            'name': 'core'
        },
        'stack size': {
            'value': 'unlimited',
            'name': 'stack'
        },
    }
    changed_vars = []
    for k, v in ulimits_items.items():
        if v['value'] == ulimits[k]:
            continue
        else:
            if set_system_conf(sudo_client, ip, v['name'], v['value'], stdio, username=username):
                changed_vars.append(k)
    changed_vars and stdio.verbose(FormatText.success('%s: ( %s ) have been successfully modified!' % (ip, ','.join(changed_vars))))
    changed_vars and stdio.print(FormatText.success('%s: ( %s ) have been successfully modified!' % (ip, (','.join(changed_vars[:5])) + '...')))
    stdio.stop_loading('succeed')

    new_client = sshclient_func(ip, username, password, stdio)
    if new_client:
        ulimits = get_ulimits(new_client)
        ulimit_check = True
        for k, v in ulimits_items.items():
            if v['value'] == ulimits[k]:
                continue
            ulimit_check = False
        if not ulimit_check:
            stdio.warn('You must reboot the following servers to ensure the ulimit parameters take effect: %s' % ip)

    for dir_path in ["/data/1", "/data/log1"]:
        change_owner_if_exists(dir_path, username, sudo_client, stdio)

    return plugin_context.return_true()
