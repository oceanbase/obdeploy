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

import _errno as err

from oblogservice_util import (
    DEFAULT_MAX_SYSLOG_FILE_COUNT,
    apply_default_log_disk_size,
    apply_default_memory_limit,
    check_resource_limits,
    get_path_disk_avail,
    parse_server_memory_stats,
)


def generate_config(
    plugin_context,
    generate_check=True,
    only_generate_password=False,
    return_generate_keys=False,
    *args,
    **kwargs,
):
    if return_generate_keys:
        return plugin_context.return_true(
            generate_keys=['memory_limit', 'log_disk_size', 'max_syslog_file_count']
        )
    if only_generate_password:
        return plugin_context.return_true()

    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_conf = cluster_config.get_global_conf()
    success = True

    stdio.start_loading('Generate oblogservice configuration')

    memory_avails = []
    disk_avails = []
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf_with_default(server)
        memory_stats = parse_server_memory_stats(client)
        if memory_stats:
            memory_avails.append(memory_stats['available'])
        elif generate_check:
            stdio.error(err.EC_OBLOGSERVICE_GET_RESOURCE_INFO_FAIL.format(
                server=server, resource='memory', key='memory_limit'))
            success = False

        home_path = server_config['home_path']
        _, disk_avail = get_path_disk_avail(client, home_path, stdio)
        if disk_avail is not None:
            disk_avails.append(disk_avail)
        elif generate_check:
            stdio.error(err.EC_OBLOGSERVICE_GET_RESOURCE_INFO_FAIL.format(
                server=server, resource='disk', key='log_disk_size'))
            success = False

    if global_conf.get('max_syslog_file_count') in (None, 0, '0'):
        cluster_config.update_global_conf(
            'max_syslog_file_count', DEFAULT_MAX_SYSLOG_FILE_COUNT, False)

    apply_default_memory_limit(cluster_config, clients, stdio)
    apply_default_log_disk_size(cluster_config, clients, stdio)

    if not check_resource_limits(cluster_config, clients, stdio):
        success = False

    if success:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
    return plugin_context.return_false()
