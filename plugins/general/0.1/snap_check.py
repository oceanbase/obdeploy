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

import hashlib
import os


def snap_check(plugin_context, snap_config, env={}, *args, **kwargs):
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    snap_hash = env.get('%s.snap_hash' % cluster_config.name)
    if not snap_hash:
        m_sum = hashlib.md5()
        m_sum.update(str(hash(cluster_config)).encode('utf-8'))
        m_sum.update(str(hash(snap_config)).encode('utf-8'))
        if 'init_file_md5' in env:
            m_sum.update(str(env['init_file_md5']).encode('utf-8'))
        snap_hash = m_sum.hexdigest()
        env['%s.snap_hash' % cluster_config.name] = snap_hash

    stdio.print('%s snap check' % cluster_config.name)
    for server in cluster_config.servers:
        home_path = cluster_config.get_server_conf(server).get('home_path')
        snap_path = os.path.join(home_path, snap_hash)
        client = clients[server]
        stdio.verbose('%s snap check' % (server))
        if not client.execute_command('[ -d %s ]' % snap_path):
            stdio.verbose('%s snap not exist: %s' % (server, snap_path))
            return 
    stdio.stop_loading('succeed')

    return plugin_context.return_true()
