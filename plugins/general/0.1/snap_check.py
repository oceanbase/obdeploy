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

    plugin_context.return_true()
