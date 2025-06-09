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


def precheck(plugin_context, host_clients, *args, **kwargs):
    def ulimit_check(host_clients, need_change_servers_vars={}, only_check=False):
        failed_check_ips = set()
        for ip, client in host_clients.items():
            if ip not in need_change_servers_vars:
                need_change_servers_vars[ip] = []
            need_change_vars = need_change_servers_vars[ip]
            server_num = len(host_clients)
            ret = client.execute_command('bash -c "ulimit -a"')
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
    kernel_check_items = [
        {'check_item': 'vm.max_map_count', 'need': [327600, 1310720], 'recommend': 655360},
        {'check_item': 'vm.min_free_kbytes', 'need': [32768, 2097152], 'recommend': 2097152},
        {'check_item': 'vm.overcommit_memory', 'need': 0, 'recommend': 0},
        {'check_item': 'fs.file-max', 'need': [6573688, float('inf')], 'recommend': 6573688},
    ]

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
    stdio.start_loading("get system config")
    for ip, client in host_clients.items():
        need_change_servers_vars[ip] = []
        need_change_vars = need_change_servers_vars[ip]
        server_num = len(host_clients)
        ret = client.execute_command('cat /proc/sys/fs/aio-max-nr /proc/sys/fs/aio-nr')
        if ret:
            max_nr, nr = ret.stdout.strip().split('\n')
            max_nr, nr = int(max_nr), int(nr)
            need = server_num * 20000
            RECD_AIO = 1048576
            if need > max_nr - nr:
                max_value = max(RECD_AIO, need)
                need_change_vars.append({'server': ip, 'var': 'fs.aio-max-nr', 'value': max_value, 'var_type': 'sysfs', 'current_value': max_nr})
            elif int(max_nr) < RECD_AIO:
                need_change_vars.append({'server': ip, 'var': 'fs.aio-max-nr', 'value': RECD_AIO, 'var_type': 'sysfs', 'current_value': max_nr})
        else:
            stdio.error(err.EC_FAILED_TO_GET_AIO_NR.format(ip=ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()

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
                elif item_value != need:
                    need_change_vars.append({'server': ip, 'var': check_item, 'value': recommend, 'var_type': 'sysfs', 'current_value': item_value})
    ulimit_check(host_clients, need_change_servers_vars)
    stdio.stop_loading('succeed')
    plugin_context.set_variable('need_change_servers_vars', need_change_servers_vars)
    plugin_context.set_variable('ulimit_check', ulimit_check)
    return plugin_context.return_true(need_change_servers_vars=need_change_servers_vars)

