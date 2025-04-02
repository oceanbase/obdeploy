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


def set_system_conf(client, server, var, value, stdio, var_type='ulimits'):
    if var_type == 'ulimits':
        if not client.execute_command('echo -e "{username} soft {name} {value}\\n{username} hard {name} {value}" | sudo tee -a /etc/security/limits.d/{name}.conf'.format(username=client.config.username,name=var, value=value)):
            return False
    else:
        ret = client.execute_command('echo "{0}={1}" | sudo tee -a /etc/sysctl.conf; sudo sysctl -p'.format(var, value))
        if not ret:
            if ret.stdout and "%s = %s" % (var, value) == ret.stdout.strip().split('\n')[-1]:
                return True
            else:
                stdio.error(err.WC_CHANGE_SYSTEM_PARAMETER_FAILED.format(server=server, key=var))
                return False
    return True


def set_sys_conf(plugin_context, ulimits_min, kernel_check_items, *args, **kwargs):
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    cluster_config = plugin_context.cluster_config

    ips_set = set()
    for server in cluster_config.servers:
        if server.ip not in ips_set:
            ips_set.add(server.ip)

    need_change_servers_vars = {}
    stdio.start_loading("get system config")
    INF = float('inf')
    for server in cluster_config.servers:
        need_change_servers_vars[server] = []
        need_change_vars = need_change_servers_vars[server]
        if server.ip not in ips_set:
            ips_set.add(server.ip)
        client = clients[server]
        server_num = len(ips_set)
        ret = client.execute_command('cat /proc/sys/fs/aio-max-nr /proc/sys/fs/aio-nr')
        if ret:
            max_nr, nr = ret.stdout.strip().split('\n')
            max_nr, nr = int(max_nr), int(nr)
            need = server_num * 20000
            RECD_AIO = 1048576
            if need > max_nr - nr:
                max_value = max(RECD_AIO, need)
                need_change_vars.append({'server': server.ip, 'var': 'fs.aio-max-nr', 'value': max_value, 'var_type': 'sysfs'})
            elif int(max_nr) < RECD_AIO:
                need_change_vars.append({'server': server.ip, 'var': 'fs.aio-max-nr', 'value': RECD_AIO, 'var_type': 'sysfs'})
        else:
            stdio.error(err.EC_FAILED_TO_GET_AIO_NR.format(ip=server.ip))
            stdio.stop_loading('fail')
            return plugin_context.return_false()
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
                stdio.error('(%s) failed to get %s. ' % (server.ip, key) + err.SUG_UNSUPPORT_OS.format().msg)
                stdio.stop_loading('fail')
                return plugin_context.return_false()
            else:
                value = int(value)
                need = ulimits_min[key]['need'](server_num)
                if need > value:
                    if ulimits_min[key].get('below_recd_error_strict', True) and value < ulimits_min[key]['recd'](server_num):
                        need = ulimits_min[key]['recd'](server_num)
                    need = need if need != INF else 'unlimited'
                    if ulimits_min[key].get('below_need_error', True):
                        need_change_vars.append({'server': server.ip, 'var': ulimits_min[key]['name'], 'value': need, 'var_type': 'ulimits'})
                else:
                    need = ulimits_min[key]['recd'](server_num)
                    if need > value:
                        need = need if need != INF else 'unlimited'
                        if ulimits_min[key].get('below_recd_error_strict', True):
                            need_change_vars.append({'server': server.ip, 'var': ulimits_min[key]['name'], 'value': need, 'var_type': 'ulimits'})

        cmd = 'sysctl -a'
        ret = client.execute_command(cmd)
        if not ret:
            stdio.error(err.EC_FAILED_TO_GET_PARAM.format(ip=server.ip, key='kernel parameter ', cmd=cmd))
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
                        need_change_vars.append({'server': server.ip, 'var': check_item, 'value': ' '.join(str(i) for i in recommend) if isinstance(recommend, list) else recommend, 'var_type': 'sysfs'})
                elif item_value != need:
                    need_change_vars.append({'server': server.ip, 'var': check_item, 'value': recommend, 'var_type': 'sysfs'})

    stdio.stop_loading('succeed')
    print_data = []
    for v in need_change_servers_vars.values():
        print_data.extend(v)
    if not print_data:
        stdio.print('No need to change system parameters')
        return plugin_context.return_true()
    stdio.print_list(print_data, ['ip', 'need_change_var', 'target_value'],
                     lambda x: [x['server'], x['var'], x['value']],
                     title='System Parameter Change List')
    if not stdio.confirm('Are you sure to change the parameters listed above ?'):
        return plugin_context.return_true()

    changed_vars = []
    success = True
    for server in cluster_config.servers:
        client = clients[server]
        client = get_root_permission_client(client, server, stdio)
        if not client:
            return plugin_context.return_false()
        need_change_vars = need_change_servers_vars[server]
        for item in need_change_vars:
            if not set_system_conf(client, server, item['var'], item['value'], stdio, item['var_type']):
                success = False
                break
            changed_vars.append(item['var'])
        stdio.print(FormatText.success('%s: ( %s ) have been successfully modified!' % (server, ','.join(changed_vars))))
    if not success:
        return plugin_context.return_false()
    return plugin_context.return_true()
