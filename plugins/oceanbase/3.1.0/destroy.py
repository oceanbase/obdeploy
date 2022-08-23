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

from _errno import EC_CLEAN_PATH_FAILED

global_ret = True


def destroy(plugin_context, *args, **kwargs):
    def clean(server, path):
        client = clients[server]
        ret = client.execute_command('rm -fr %s/' % (path), timeout=-1)
        if not ret:
            # print stderror
            global global_ret
            global_ret = False
            stdio.warn(EC_CLEAN_PATH_FAILED.format(server=server, path=path))
        else:
            stdio.verbose('%s:%s cleaned' % (server, path))
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    stdio.start_loading('observer work dir cleaning')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s work path cleaning', server)
        clean(server, server_config['home_path'])
        for key in ['data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']:
            if server_config.get(key):
                clean(server, server_config[key])
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')
