# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function

import re

import _errno as err


def system_limits_check(plugin_context, generate_configs={}, strict_check=False, *args, **kwargs):
    stdio = plugin_context.stdio

    servers_clients = plugin_context.get_variable('servers_clients')
    alert = plugin_context.get_variable('alert')
    alert_strict = plugin_context.get_variable('alert_strict')
    critical = plugin_context.get_variable('critical')
    servers_memory = plugin_context.get_variable('servers_memory')
    servers_disk = plugin_context.get_variable('servers_disk')
    production_mode = plugin_context.get_variable('production_mode')
    kernel_check = plugin_context.get_variable('kernel_check')
    kernel_check_items = plugin_context.get_variable('kernel_check_items')
    max_user_processes = plugin_context.get_variable('max_user_processes')

    INF = float('inf')

    need_check_servers_disk = {}
    for ip in servers_disk:
        client = servers_clients[ip]
        ip_servers = servers_memory[ip]['servers'].keys()
        server_num = len(ip_servers)

        ret = client.execute_command('cat /proc/sys/fs/aio-max-nr /proc/sys/fs/aio-nr')
        if not ret:
            for server in ip_servers:
                critical(server, 'aio', err.EC_FAILED_TO_GET_AIO_NR.format(ip=ip), [err.SUG_CONNECT_EXCEPT.format()])
        else:
            try:
                max_nr, nr = ret.stdout.strip().split('\n')
                max_nr, nr = int(max_nr), int(nr)
                need = server_num * 20000
                RECD_AIO = 1048576
                if need > max_nr - nr:
                    for server in ip_servers:
                        critical(server, 'aio', err.EC_AIO_NOT_ENOUGH.format(ip=ip, avail=max_nr - nr, need=need), [err.SUG_SYSCTL.format(var='fs.aio-max-nr', value=max(RECD_AIO, need), ip=ip)])
                elif int(max_nr) < RECD_AIO:
                    for server in ip_servers:
                        alert(server, 'aio', err.WC_AIO_NOT_ENOUGH.format(ip=ip, current=max_nr), [err.SUG_SYSCTL.format(var='fs.aio-max-nr', value=RECD_AIO, ip=ip)])
            except:
                for server in ip_servers:
                    alert(server, 'aio', err.EC_FAILED_TO_GET_AIO_NR.format(ip=ip), [err.SUG_UNSUPPORT_OS.format()])
                stdio.exception('')

        ret = client.execute_command('ulimit -a')
        ulimits_min = {
            'open files': {
                'need': lambda x: 20000 * x,
                'recd': lambda x: 655350,
                'name': 'nofile'
            },
            'max user processes': max_user_processes,
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
        ulimits = {}
        src_data = re.findall('\s?([a-zA-Z\s]+[a-zA-Z])\s+\([a-zA-Z\-,\s]+\)\s+([\d[a-zA-Z]+)', ret.stdout) if ret else []
        for key, value in src_data:
            ulimits[key] = value
        for key in ulimits_min:
            value = ulimits.get(key)
            if value == 'unlimited':
                continue
            if not value or not (value.strip().isdigit()):
                for server in ip_servers:
                    alert(server, 'ulimit', '(%s) failed to get %s' % (ip, key), suggests=[err.SUG_UNSUPPORT_OS.format()])
            else:
                value = int(value)
                need = ulimits_min[key]['need'](server_num)
                if need > value:
                    if (strict_check or production_mode) and ulimits_min[key].get('below_recd_error_strict', True) and value < ulimits_min[key]['recd'](server_num):
                        need = ulimits_min[key]['recd'](server_num)
                    need = need if need != INF else 'unlimited'
                    for server in ip_servers:
                        if ulimits_min[key].get('below_need_error', True):
                            critical(server, 'ulimit', err.EC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value), [err.SUG_ULIMIT.format(name=ulimits_min[key]['name'], value=need, ip=ip)])
                        else:
                            alert(server, 'ulimit', err.EC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value), suggests=[err.SUG_ULIMIT.format(name=ulimits_min[key]['name'], value=need, ip=ip)])
                else:
                    need = ulimits_min[key]['recd'](server_num)
                    if need > value:
                        need = need if need != INF else 'unlimited'
                        for server in ip_servers:
                            if ulimits_min[key].get('below_recd_error_strict', True):
                                alert(server, 'ulimit', err.WC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value), suggests=[err.SUG_ULIMIT.format(name=ulimits_min[key]['name'], value=need, ip=ip)])
                            else:
                                stdio.warn(err.WC_ULIMIT_CHECK.format(server=ip, key=key, need=need, now=value))

        if kernel_check:
            # check kernel params
            try:
                for server in plugin_context.cluster_config.servers:
                    if ip == server.ip:
                        break
                cmd = 'sysctl -a'
                ret = client.execute_command(cmd)
                if not ret:
                    alert_strict(server, 'kernel', err.EC_FAILED_TO_GET_PARAM.format(key='kernel parameter ', cmd=cmd), [err.SUG_CONNECT_EXCEPT.format(ip=ip)])
                    continue
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
                                suggest = [err.SUG_SYSCTL.format(var=check_item, value=' '.join(str(i) for i in recommend) if isinstance(recommend, list) else recommend, ip=ip)]
                                need = 'within {}'.format(needs) if needs[-1] != INF else 'greater than {}'.format(needs[0])
                                now = '[{}]'.format(', '.join(values)) if len(values) > 1 else item_value
                                alert_strict(server, check_item, err.EC_PARAM_NOT_IN_NEED.format(ip=ip, check_item=check_item, need=need, now=now, recommend=recommends), suggest)
                                break
                        elif item_value != need:
                            alert_strict(server, check_item, err.EC_PARAM_NOT_IN_NEED.format(ip=ip, check_item=check_item, need=needs, recommend=recommend, now=item_value), [err.SUG_SYSCTL.format(var=check_item, value=recommend, ip=ip)])
            except:
                stdio.exception('')

        need_check_servers_disk[ip] = servers_disk[ip]

    plugin_context.set_variable('need_check_servers_disk', need_check_servers_disk)

    return plugin_context.return_true()

