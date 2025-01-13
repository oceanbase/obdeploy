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
