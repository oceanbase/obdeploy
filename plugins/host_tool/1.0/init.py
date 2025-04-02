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
from _stdio import FormatText
from ssh import get_root_permission_client


def set_system_conf(client, ip, var, value, stdio, var_type='ulimits'):
    if var_type == 'ulimits':
        if not client.execute_command('echo -e "{username} soft {name} {value}\\n{username} hard {name} {value}" | sudo tee -a /etc/security/limits.d/{name}.conf'.format(username=client.config.username,name=var, value=value)):
            return False
    else:
        ret = client.execute_command('echo "{0}={1}" | sudo tee -a /etc/sysctl.conf; sudo sysctl -p'.format(var, value))
        if not ret:
            if ret.stdout and "%s = %s" % (var, value) == ret.stdout.strip().split('\n')[-1]:
                return True
            else:
                stdio.error(err.WC_CHANGE_SYSTEM_PARAMETER_FAILED.format(server=ip, key=var))
                return False
    return True


def init(plugin_context, host_clients, need_change_servers_vars, ulimit_check=None,*args, **kwargs):
    stdio = plugin_context.stdio
    changed_vars = []
    success = True
    for ip, client in host_clients.items():
        need_change_vars = need_change_servers_vars[ip]
        for item in need_change_vars:
            if not set_system_conf(client, ip, item['var'], item['value'], stdio, item['var_type']):
                success = False
                break
            changed_vars.append(item['var'])
        changed_vars and stdio.print(FormatText.success('%s: ( %s ) have been successfully modified!' % (ip, ','.join(changed_vars))))
    need_reboot_ips = ulimit_check(host_clients, only_check=True)
    if not success:
        return plugin_context.return_false()
    return plugin_context.return_true(need_reboot_ips=need_reboot_ips)
