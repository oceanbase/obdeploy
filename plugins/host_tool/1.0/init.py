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

from _stdio import FormatText
from tool import set_system_conf, get_option, get_sudo_prefix


def init(plugin_context, host_clients, need_change_servers_vars, machine_check_items, ulimit_check=None, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
    changed_vars = []
    success = True
    for ip, client in host_clients.items():
        sudo_prefix = get_sudo_prefix(client)
        if not machine_check_items[ip]['firewalld']:
            firewalld_disable = True
            stdio.start_loading("disabling firewalld")
            if client.execute_command('cat /etc/redhat-release'):
                firewalld_name = 'firewalld'
            else:
                firewalld_name = 'ufw'
            if client.execute_command('systemctl is-active %s ' % firewalld_name).stdout.strip() == 'active':
                if not client.execute_command(sudo_prefix + 'systemctl stop %s' % firewalld_name):
                    firewalld_disable = False
            if client.execute_command('systemctl is-enabled %s' % firewalld_name).stdout.strip() == 'enabled':
                if not client.execute_command(sudo_prefix + 'systemctl disable %s' % firewalld_name):
                    firewalld_disable = False
            stdio.stop_loading('succeed' if firewalld_disable else 'fail')
        if not machine_check_items[ip]['selinux']:
            selinux_disable = False
            stdio.start_loading("disabling selinux")
            if client.execute_command(f"{sudo_prefix}sed -i 's/^SELINUX=.*/SELINUX=disabled/' /etc/selinux/config; {sudo_prefix}setenforce 0"):
                selinux_disable = True
            stdio.stop_loading('succeed' if selinux_disable else 'fail')

        if not machine_check_items[ip]['dir_check']:
            chown_dir = True
            stdio.start_loading("chown dir")
            username = get_option(options, 'username', client.config.username)
            for dir_path in ["/data/1", "/data/log1"]:
                if not client.execute_command(sudo_prefix + 'chown -R %s %s' % (username, dir_path)):
                    chown_dir = False
            stdio.stop_loading('succeed' if chown_dir else 'fail')
        if not machine_check_items[ip]['transparent_hugepage']:
            transparent_hugepage = False
            stdio.start_loading("disable transparent_hugepage")
            if client.execute_command(f"echo never | {sudo_prefix} tee /sys/kernel/mm/transparent_hugepage/enabled"):
                transparent_hugepage = True
            stdio.stop_loading('succeed' if transparent_hugepage else 'fail')
        if not machine_check_items[ip]['network_card']:
            network_card = False
            stdio.start_loading("set net card MTY value")
            ret = client.execute_command("ip route | grep default | awk '{print $5}' | head -n1")
            if ret:
                card_name = ret.stdout.strip()
                if client.execute_command(f"{sudo_prefix} sed -i 's/^MTU=.*/MTU=1500/' /etc/sysconfig/network-scripts/ifcfg-{card_name}") and client.execute_command(sudo_prefix + "systemctl restart network"):
                    network_card = True
            stdio.stop_loading('succeed' if network_card else 'fail')

        need_change_vars = need_change_servers_vars[ip]
        need_change_vars and stdio.print("modify system parameters")
        for item in need_change_vars:
            if not set_system_conf(client, ip, item['var'], item['value'], stdio, item['var_type'], username=get_option(options, 'username')):
                success = False
                break
            changed_vars.append(item['var'])
        changed_vars and stdio.verbose(FormatText.success('%s: ( %s ) have been successfully modified!' % (ip, ','.join(changed_vars))))
        changed_vars and stdio.print(FormatText.success('%s: ( %s ) have been successfully modified!' % (ip, (','.join(changed_vars[:5])) + '...')))
    need_reboot_ips = ulimit_check(host_clients, only_check=True)
    if not success:
        return plugin_context.return_false()
    return plugin_context.return_true(need_reboot_ips=need_reboot_ips)
