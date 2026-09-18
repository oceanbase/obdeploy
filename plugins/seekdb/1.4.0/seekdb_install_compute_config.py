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

"""Compute the interactive SeekDB 1.4 configuration from host resources."""

from __future__ import absolute_import, division, print_function


def _fmt_cap(value):
    if value >= 1024 ** 4:
        return '%dT' % (value // (1024 ** 4))
    if value >= 1024 ** 3:
        return '%dG' % (value // (1024 ** 3))
    if value >= 1024 ** 2:
        return '%dM' % (value // (1024 ** 2))
    return '%d' % value


def seekdb_install_compute_config(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    resources = plugin_context.get_variable('resources')
    base_info = plugin_context.get_variable('base_info', spacename='interactive')
    if not resources or not base_info:
        stdio.error('resources or base_info not in namespace.')
        return plugin_context.return_false()

    total_mem = resources['total_mem']
    free_disk_bytes = resources['free_disk_bytes']
    clog_avail_bytes = resources['clog_avail_bytes']
    clog_min_init = 2 * (1024 ** 3)
    install_mode = plugin_context.get_variable('install_mode', spacename='interactive') or 'standalone'
    run_mode = plugin_context.get_variable('install_run_mode', spacename='interactive') or 'dev'

    if run_mode == 'dev':
        memory_budget = 1 * (1024 ** 3)
        datafile_bytes = min(20 * (1024 ** 3), free_disk_bytes) if free_disk_bytes else 20 * (1024 ** 3)
        syslog_count = 2
    else:
        base_mem = plugin_context.get_variable('prod_memory_base', spacename='interactive') or int(total_mem * 0.9)
        strategy = plugin_context.get_variable('prod_memory_strategy', spacename='interactive')
        if strategy == 1:
            memory_budget = plugin_context.get_variable('prod_hard_limit', spacename='interactive') or int(base_mem * 0.9)
        else:
            memory_budget = int(base_mem * 5 / 9)
        datafile_bytes = int(free_disk_bytes * 0.8) if free_disk_bytes else 20 * (1024 ** 3)
        syslog_count = 1024

    if install_mode in ('primary', 'standby'):
        log_disk_size = 3 * memory_budget
    else:
        log_disk_size = max(clog_min_init, memory_budget // 2)
    if clog_avail_bytes < log_disk_size:
        stdio.error('Clog directory free space < required (%s).' % _fmt_cap(log_disk_size))
        return plugin_context.return_false()

    config_list = [
        ('IP', base_info['ip']),
        ('User', base_info['user']),
        ('ssh_port', str(base_info.get('ssh_port', '22'))),
        ('home_path', base_info.get('home_path', '')),
        ('data_dir', base_info['data_dir']),
        ('redo_dir', base_info['redo_dir']),
        ('mysql_port', str(base_info.get('mysql_port', '2881'))),
        ('memory_budget', _fmt_cap(memory_budget)),
        ('datafile_maxsize', _fmt_cap(datafile_bytes)),
        ('max_syslog_file_count', str(syslog_count)),
        ('log_disk_size', _fmt_cap(log_disk_size)),
        ('auto_start', str(base_info.get('auto_start', False))),
    ]
    config_list.insert(7, ('obshell_port', str(base_info.get('obshell_port', '2886'))))
    if base_info.get('rpc_port'):
        index = next((i for i, (key, _) in enumerate(config_list) if key == 'mysql_port'), -1)
        if index >= 0:
            config_list.insert(index + 1, ('rpc_port', base_info['rpc_port']))

    plugin_context.set_variable('config_list', config_list)
    return plugin_context.return_true()
