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

"""SeekDB install: compute config from resources and run mode. Primary/standby: log_disk_size = 3 * memory_limit."""

from __future__ import absolute_import, division, print_function

from _types import Capacity


def _fmt_cap(b):
    if b >= 1024 ** 4:
        return '%dT' % (b // (1024 ** 4))
    if b >= 1024 ** 3:
        return '%dG' % (b // (1024 ** 3))
    if b >= 1024 ** 2:
        return '%dM' % (b // (1024 ** 2))
    return '%d' % b


def seekdb_install_compute_config(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    resources = plugin_context.get_variable('resources')
    base_info = plugin_context.get_variable('base_info', spacename='interactive')
    if not resources or not base_info:
        stdio.error('resources or base_info not in namespace.')
        return plugin_context.return_false()
    total_mem = resources['total_mem']
    avail_mem = resources['avail_mem']
    free_disk_bytes = resources['free_disk_bytes']
    clog_avail_bytes = resources['clog_avail_bytes']
    CLOG_MIN_INIT = 2 * (1024 ** 3)
    install_mode = plugin_context.get_variable('install_mode', spacename='interactive') or 'standalone'
    run_mode = plugin_context.get_variable('install_run_mode', spacename='interactive') or 'dev'
    if run_mode == 'dev':
        soft_mem = 1 * (1024 ** 3)
        hard_mem = min(total_mem, 4 * (1024 ** 3))
        datafile_bytes = min(20 * (1024 ** 3), free_disk_bytes) if free_disk_bytes else 20 * (1024 ** 3)
        syslog_count = 2
        log_disk_size = max(CLOG_MIN_INIT, (hard_mem // 2))
    else:
        base_mem = plugin_context.get_variable('prod_memory_base', spacename='interactive') or int(total_mem * 0.9)
        hard_mem = plugin_context.get_variable('prod_hard_limit', spacename='interactive') or int(base_mem * 0.9)
        strategy = plugin_context.get_variable('prod_memory_strategy', spacename='interactive')
        if strategy == 1:
            soft_mem = hard_mem
        else:
            soft_mem = int(base_mem * 5/9)
        datafile_bytes = int(free_disk_bytes * 0.8) if free_disk_bytes else 20 * (1024 ** 3)
        syslog_count = 1024
        log_disk_size = max(CLOG_MIN_INIT, (soft_mem // 2))
    memory_limit = soft_mem
    memory_hard_limit = hard_mem
    if install_mode in ('primary', 'standby'):
        log_disk_size = 3 * memory_limit
        log_disk_size_str = _fmt_cap(log_disk_size)
    else:
        log_disk_size_str = _fmt_cap(log_disk_size)
    if install_mode in ('primary', 'standby'):
        clog_required = log_disk_size
    else:
        clog_required = max(CLOG_MIN_INIT, memory_hard_limit // 2)
    if clog_avail_bytes < clog_required:
        stdio.error('Clog directory free space < required (%s).' % _fmt_cap(clog_required))
        return plugin_context.return_false()
    ip = base_info['ip']
    user = base_info['user']
    home_path = base_info.get('home_path', '')
    data_dir = base_info['data_dir']
    redo_dir = base_info['redo_dir']
    mysql_port = base_info.get('mysql_port', '2881')
    obshell_port = str(base_info.get('obshell_port', '2886'))
    auto_start = base_info.get('auto_start', False)
    ssh_port = str(base_info.get('ssh_port', '22'))
    config_list = [
        ('IP', ip), ('User', user), ('ssh_port', ssh_port), ('home_path', home_path), ('data_dir', data_dir), ('redo_dir', redo_dir),
        ('mysql_port', str(mysql_port)),
        ('memory_limit', _fmt_cap(memory_limit)), ('memory_hard_limit', _fmt_cap(memory_hard_limit)),
        ('datafile_maxsize', _fmt_cap(datafile_bytes)),
        ('max_syslog_file_count', str(syslog_count)), ('log_disk_size', log_disk_size_str),
        ('auto_start', str(auto_start)),
    ]
    if install_mode != 'standby':
        config_list.insert(7, ('obshell_port', obshell_port))
    if base_info.get('rpc_port'):
        idx = next((i for i, (k, _) in enumerate(config_list) if k == 'mysql_port'), -1)
        if idx >= 0:
            config_list.insert(idx + 1, ('rpc_port', base_info['rpc_port']))
    plugin_context.set_variable('config_list', config_list)
    return plugin_context.return_true()
