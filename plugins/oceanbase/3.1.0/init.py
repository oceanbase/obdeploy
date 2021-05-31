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


def init(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    stdio.verbose('option `force` is %s' % force)
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        stdio.print('%s initializes cluster work home', server)
        if force:
            ret = client.execute_command('rm -fr %s/*' % home_path)
            if not ret:
                global_ret = False
                stdio.error('failed to initialize %s home path: %s' % (server, ret.stderr))
                continue
        else:
            if client.execute_command('mkdir -p %s' % home_path):
                ret = client.execute_command('ls %s' % (home_path))
                if not ret or ret.stdout.strip():
                    global_ret = False
                    stdio.error('fail to init %s home path: %s is not empty' % (server, home_path))
                    continue
            else:
                stdio.error('fail to init %s home path: create %s failed' % (server, home_path))
        ret = client.execute_command('mkdir -p %s/{etc,admin,.conf,log}' % home_path)
        if ret:
            data_path = server_config['data_dir'] if 'data_dir' in server_config else '%s/store' % home_path
            if force:
                ret = client.execute_command('rm -fr %s/*' % data_path)
                if not ret:
                    global_ret = False
                    stdio.error('fail to init %s data path: %s permission denied' % (server, ret.stderr))
                    continue
            else:
                if client.execute_command('mkdir -p %s' % data_path):
                    ret = client.execute_command('ls %s' % (data_path))
                    if not ret or ret.stdout.strip():
                        global_ret = False
                        stdio.error('fail to init %s data path: %s is not empty' % (server, data_path))
                        continue
                else:
                    stdio.error('fail to init %s data path: create %s failed' % (server, data_path))
            ret = client.execute_command('mkdir -p %s/{sstable,clog,ilog,slog}' % data_path)
            if ret:
                data_path != '%s/store' % home_path and client.execute_command('ln -sf %s %s/store' % (data_path, home_path))
            else:
                global_ret = False
                stdio.error('failed to initialize %s date path', server)
        else:
            global_ret = False
            stdio.error('fail to init %s home path: %s permission denied' % (server, ret.stderr))
    global_ret and plugin_context.return_true()
