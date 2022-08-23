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

import os

from _deploy import RsyncConfig


def rsync(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    rsync_configs = cluster_config.get_rsync_list()
    if not rsync_configs:
        return plugin_context.return_true()

    stdio.start_loading("Synchronizing runtime dependencies")
    succeed = True
    for rsync_config in rsync_configs:
        source_path = rsync_config.get(RsyncConfig.SOURCE_PATH)
        target_path = rsync_config.get(RsyncConfig.TARGET_PATH)
        if os.path.isabs(target_path):
            rsync_config[RsyncConfig.TARGET_PATH] = os.path.normpath('./' + target_path)

    sub_io = stdio.sub_io()
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        for rsync_config in rsync_configs:
            source_path = rsync_config.get(RsyncConfig.SOURCE_PATH)
            target_path = rsync_config.get(RsyncConfig.TARGET_PATH)
            if os.path.isdir(source_path):
                stdio.verbose('put local dir %s to %s: %s.' % (source_path, server, target_path))
                if not client.put_dir(source_path, os.path.join(home_path, target_path), stdio=sub_io):
                    stdio.warn('failed to put local dir %s to %s: %s.' % (source_path, server, target_path))
                    succeed = False
            elif os.path.exists(source_path):
                stdio.verbose('put local file %s to %s: %s.' % (source_path, server, target_path))
                if not client.put_file(source_path, os.path.join(home_path, target_path), stdio=sub_io):
                    stdio.warn('failed to put local file %s to %s: %s.' % (source_path, server, target_path))
                    succeed = False
            else:
                stdio.verbose('%s is not found.' % source_path)
    if succeed:
        stdio.stop_loading("succeed")
        return plugin_context.return_true()
    else:
        stdio.stop_loading("fail")
        return plugin_context.return_false()
