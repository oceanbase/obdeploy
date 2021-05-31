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


def destroy(plugin_context, *args, **kwargs):
    def clean(server, path):
        client = clients[server]
        ret = client.execute_command('rm -fr %s/* %s/.conf' % (path, path))
        if not ret:
            # pring stderror
            global_ret = False
            stdio.warn('fail to clean %s:%s', (server, path))
        else:
            stdio.verbose('%s:%s cleaned' % (server, path))
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_ret = True
    stdio.start_loading('obproxy work dir cleaning')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s work path cleaning', server)
        clean(server, server_config['home_path'])
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')