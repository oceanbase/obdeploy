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
import _errno as err
import const
from _arch import getBaseArch
from _environ import ENV_OBD_WEB_TYPE
from _stdio import FormatText
from _types import Capacity
from tool import get_option, get_sudo_prefix, COMMAND_ENV


def precheck(plugin_context, host_clients, print_recommend_cmd=True, *args, **kwargs):
    def ulimit_check(host_clients, need_change_servers_vars={}, only_check=False, username=None):
        failed_check_ips = set()
        for ip, client in host_clients.items():
            if ip not in need_change_servers_vars:
                need_change_servers_vars[ip] = []
            need_change_vars = need_change_servers_vars[ip]
            server_num = len(host_clients)
            if not username:
                ret = client.execute_command('bash -c "ulimit -a"')
            else:
                sudo_prefix = get_sudo_prefix(client)
                ret = client.execute_command(sudo_prefix + '-u %s bash -c "ulimit -a"' % username)
            ulimits = {}
            src_data = re.findall('\s?([a-zA-Z\s]+[a-zA-Z])\s+\([a-zA-Z\-,\s]+\)\s+([\d[a-zA-Z]+)',ret.stdout) if ret else []
            for key, value in src_data:
                ulimits[key] = value
            for key in ulimits_min:
                value = ulimits.get(key)
                if value == 'unlimited':
                    continue
                if not value or not (value.strip().isdigit()):
                    stdio.waring('(%s) failed to get %s. ' % (ip, key) + err.SUG_UNSUPPORT_OS.format().msg)
                else:
                    value = int(value)
                    need = ulimits_min[key]['need'](server_num)
                    if need > value:
                        if ulimits_min[key].get('below_recd_error_strict', True) and value < ulimits_min[key]['recd'](server_num):
                            need = ulimits_min[key]['recd'](server_num)
                        need = need if need != INF else 'unlimited'
                        if ulimits_min[key].get('below_need_error', True):
                            failed_check_ips.add(ip)
                            not only_check and need_change_vars.append({'server': ip, 'var': ulimits_min[key]['name'], 'value': need, 'var_type': 'ulimits', 'current_value': value})
                    else:
                        need = ulimits_min[key]['recd'](server_num)
                        if need > value:
                            need = need if need != INF else 'unlimited'
                            if ulimits_min[key].get('below_recd_error_strict', True):
                                failed_check_ips.add(ip)
                                not only_check and need_change_vars.append({'server': ip, 'var': ulimits_min[key]['name'], 'value': need, 'var_type': 'ulimits', 'current_value': value})
        return failed_check_ips

    stdio = plugin_context.stdio
    options = plugin_context.options
    stdio.start_loading("get system config")
    error_msgs = []
    warn_msgs = []
    machine_check_items = {}
    for ip, client in host_clients.items():
        sudo_prefix = get_sudo_prefix(client)
        check_items = {
            "firewalld": True,
            "selinux": True,
            "network_tool": True,
            "dir_check": True,
            "cpu": True,
        }
        machine_check_items[ip] = check_items
        ret = client.execute_command('cat /proc/meminfo')
        for k, v in re.findall('(\w+)\s*:\s*(\d+\s*\w+)', ret.stdout):
            if k == 'MemAvailable' and Capacity(str(v)).bytes < 3 << 30:
                error_msgs.append("The minimum memory must not be less than 3 GB.")

        if client.execute_command('cat /etc/redhat-release'):
            firewalld_name = 'firewalld'
        else:
            firewalld_name = 'ufw'
        if client.execute_command('systemctl is-active %s ' % firewalld_name).stdout.strip() == 'active':
            warn_msgs.append("The firewall service %s is active." % firewalld_name)
            check_items['firewalld'] = False

        if client.execute_command('systemctl is-enabled %s' % firewalld_name).stdout.strip() == 'enabled':
            warn_msgs.append("The firewall %s auto-start service is not disabled." % firewalld_name)
            check_items['firewalld'] = False

        getenforce_ret = client.execute_command('/usr/sbin/getenforce')
        if getenforce_ret and getenforce_ret.stdout.strip() != 'Disabled':
            warn_msgs.append("SELinux is not in a disabled state.")
            check_items['selinux'] = False

        user_check = True
        username = get_option(options, 'username', client.config.username)
        if username != 'root' and not client.execute_command(f'{sudo_prefix}ls /home/{username}'):
            warn_msgs.append(f"The /home/{username} directory does not exist.")
            user_check = False
        pwdauth_ret = client.execute_command(sudo_prefix + 'grep "^PasswordAuthentication" /etc/ssh/sshd_config').stdout.strip()
        if not pwdauth_ret or not pwdauth_ret.find('yes') != -1:
            warn_msgs.append("Password login permission is not enabled.")
            user_check = False
        if username != 'root':
            cmd = sudo_prefix + '-l -U %s' % username
            if not ("NOPASSWD" in client.execute_command(cmd).stdout):
                warn_msgs.append(f"The %s user's sudo privileges are not configured for password-free access." % username)
                user_check = False

        if not client.execute_command('which ifconfig'):
            warn_msgs.append("The net-tools package is not installed.")
            check_items['network_tool'] = False

        need_chown_dirs = []
        for dir_path in ['/data/1', '/data/log1']:
            if client.execute_command(f'ls {dir_path}'):
                owner = client.execute_command(f"stat -c '%U' {dir_path}").stdout.strip()
                if owner != username:
                    need_chown_dirs.append(dir_path)
                    check_items['dir_check'] = False
        if need_chown_dirs:
            warn_msgs.append(f"The owner of the {need_chown_dirs} directory is not %s." % username)
        basearch = getBaseArch()
        stdio.verbose("basearch: %s" % basearch)
        if 'x86' in basearch:
            if len(re.findall(r'(^avx\s+)|(\s+avx\s+)|(\s+avx$)', client.execute_command('lscpu | grep avx').stdout)) == 0:
                error_msgs.append("The machine's cpu cannot support avx. This error can be ignored for the following oceanbase versions:\n[4.2.5.6, 4.3.0.0)\n[4.3.5.4, 4.4.0.0)\n[4.4.1.0, +∞)")
        elif 'arm' in basearch or 'aarch' in basearch:
            if len(re.findall(r'(^atomics\s+)|(\s+atomics\s+)|(\s+atomics$)', client.execute_command('lscpu | grep atomics').stdout)) == 0:
                error_msgs.append("The machine's cpu cannot support LSE.This error can be safely ignored when using OceanBase with non-LSE RPM packages.")

        if client.execute_command("uname -r | cut -d'-' -f1").stdout.strip() < '3.1':
            error_msgs.append("The machine's kernel cannot be lower than 3.1")

    kernel_check_items = [
        {'check_item': 'fs.aio-max-nr', 'recommend': 1048576, 'need': [1048576, float('inf')]},
        {'check_item': 'net.core.somaxconn', 'recommend': 2048, 'need': [2048, float('inf')]},
        {'check_item': 'net.core.netdev_max_backlog', 'recommend': 10000, 'need': [10000, float('inf')]},
        {'check_item': 'net.core.rmem_default', 'recommend': 16777216, 'need': [16777216, float('inf')]},
        {'check_item': 'net.core.wmem_default', 'recommend': 16777216, 'need': [16777216, float('inf')]},
        {'check_item': 'net.core.rmem_max', 'recommend': 16777216, 'need': [16777216, float('inf')]},
        {'check_item': 'net.core.wmem_max', 'recommend': 16777216, 'need': [16777216, float('inf')] },
        {'check_item': 'net.ipv4.conf.default.rp_filter', 'recommend': 1, 'need': 1},
        {'check_item': 'net.ipv4.conf.default.accept_source_route', 'recommend': 0, 'need': 0},
        {'check_item': 'net.ipv4.tcp_syncookies', 'recommend': 1, 'need': 1},
        {'check_item': 'net.ipv4.tcp_rmem', 'recommend': [4096, 87380, 16777216], 'need': ([4096, float('inf')], [87380, float('inf')], [16777216, float('inf')])},
        {'check_item': 'net.ipv4.tcp_wmem', 'recommend': [4096, 65536, 16777216], 'need': ([4096, float('inf')], [65536, float('inf')], [16777216, float('inf')])},
        {'check_item': 'net.ipv4.tcp_max_syn_backlog', 'recommend': 16384, 'need': [16384, float('inf')]},
        {'check_item': 'net.ipv4.tcp_fin_timeout', 'recommend': 15, 'need': 15},
        {'check_item': 'net.ipv4.tcp_slow_start_after_idle', 'recommend': 0, 'need': 0},
        {'check_item': 'vm.swappiness', 'recommend': 0, 'need': 0},
        {'check_item': 'vm.min_free_kbytes', 'recommend': 2097152, 'need': [2097152, float('inf')]},
        {'check_item': 'vm.overcommit_memory', 'recommend': 0, 'need': 0},
        {'check_item': 'fs.file-max', 'recommend': 6573688, 'need': [6573688, float('inf')]},
        {'check_item': 'fs.pipe-user-pages-soft', 'recommend': 0, 'need': 0},
        {'check_item': 'vm.max_map_count', 'recommend': 655360, 'need': [655360, float('inf')]},
        {'check_item': 'kernel.core_pattern', 'recommend': '/data/core-%e-%p-%t', 'need': '/data/core-%e-%p-%t'}
    ]
    if COMMAND_ENV.get(ENV_OBD_WEB_TYPE, '') == const.COMP_OB_STANDALONE:
        kernel_check_items.append({'check_item': 'net.ipv4.ip_forward', 'recommend': 0, 'need': 0})

    INF = float('inf')
    ulimits_min = {
        'open files': {
            'need': lambda x: 20000 * x,
            'recd': lambda x: 655350,
            'name': 'nofile'
        },
        'max user processes': {
            'need': lambda x: 4096,
            'recd': lambda x: 4096 * x,
            'name': 'nproc'
        },
        'core file size': {
            'need': lambda x: 0,
            'recd': lambda x: INF,
            'below_need_error': False,
            'below_recd_error_strict': False,
            'name': 'core'
        },
        'stack size': {
            'need': lambda x: 1024,
            'recd': lambda x: INF,
            'below_recd_error_strict': False,
            'name': 'stack'
        },
    }

    need_change_servers_vars = {}
    for ip, client in host_clients.items():
        need_change_servers_vars[ip] = []
        need_change_vars = need_change_servers_vars[ip]

        cmd = 'sysctl -a'
        ret = client.execute_command(cmd)
        if not ret:
            stdio.error(err.EC_FAILED_TO_GET_PARAM.format(ip=ip, key='kernel parameter ', cmd=cmd))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        kernel_params = {}
        kernel_param_src = ret.stdout.split('\n')
        for kernel in kernel_param_src:
            if not kernel:
                continue
            kernel = kernel.split('=')
            kernel_params[kernel[0].strip()] = re.findall(r"[-+]?\d+", kernel[1])
        for kernel_param in kernel_check_items:
            check_item = kernel_param['check_item']
            if check_item not in kernel_params:
                continue
            values = kernel_params[check_item]
            needs = kernel_param['need']
            recommends = kernel_param['recommend']
            for i in range(len(values)):
                # This case is not handling the value of 'default'. Additional handling is required for 'default' in the future.
                item_value = int(values[i])
                need = needs[i] if isinstance(needs, tuple) else needs
                recommend = recommends[i] if isinstance(recommends, tuple) else recommends
                if isinstance(need, list):
                    if item_value < need[0] or item_value > need[1]:
                        need_change_vars.append({'server': ip, 'var': check_item, 'value': ' '.join(str(i) for i in recommend) if isinstance(recommend, list) else recommend, 'var_type': 'sysfs', 'current_value': item_value})
                        break
                elif item_value != need:
                    need_change_vars.append({'server': ip, 'var': check_item, 'value': recommend, 'var_type': 'sysfs', 'current_value': item_value})
    ulimit_check(host_clients, need_change_servers_vars, username=get_option(options, 'username'))
    stdio.stop_loading('succeed')

    for warn_msgs in warn_msgs:
        print_recommend_cmd and stdio.warn(warn_msgs)
    for error_msgs in error_msgs:
        print_recommend_cmd and stdio.error(error_msgs)
    print_data = []
    for v in need_change_servers_vars.values():
        print_data.extend(v)
    if not print_data:
        stdio.print(FormatText.success('No need to change system parameters'))
    else:
        stdio.print_list(print_data, ['ip', 'name', 'current_value', 'expected_value'],
                     lambda x: [x['server'], x['var'], x['current_value'], x['value']],
                     title='System Parameter Change List')
    if not user_check and print_recommend_cmd:
        stdio.print(FormatText.success(f"Please run `obd host user init -u {username} --host={client.config.host}` to init user."))
    if not check_items['network_tool'] and print_recommend_cmd:
        stdio.print(FormatText.success("please run: `yum install net-tools` or `sudo apt install net-tools`"))
    if (warn_msgs or error_msgs or print_data) and print_recommend_cmd:
        stdio.print(FormatText.success(f"""Please run `obd host init {client.config.username} {client.config.host}{" -p '******'" if client.config.password else ''}{' -u '+get_option(options, 'username') if get_option(options, 'username') else ''}` to init host."""))
    plugin_context.set_variable('machine_check_items', machine_check_items)
    plugin_context.set_variable('need_change_servers_vars', need_change_servers_vars)
    plugin_context.set_variable('ulimit_check', ulimit_check)
    return plugin_context.return_true(need_change_servers_vars=need_change_servers_vars)

