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


def init(plugin_context, local_home_path, repository_dir, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    stdio.start_loading('Initializes obagent work home')
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        remote_home_path = client.execute_command('echo $HOME/.obd').stdout.strip()
        remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
        stdio.verbose('%s init cluster work home', server)
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
                global_ret = False
                stdio.error('fail to init %s home path: create %s failed' % (server, home_path))
                continue

        if not (client.execute_command("bash -c 'mkdir -p %s/{run,bin,lib,conf,log}'" % (home_path)) \
         and client.execute_command("cp -r %s/conf %s/" % (remote_repository_dir, home_path)) \
         and client.execute_command("if [ -d %s/bin ]; then ln -fs %s/bin/* %s/bin; fi" % (remote_repository_dir, remote_repository_dir, home_path)) \
         and client.execute_command("if [ -d %s/lib ]; then ln -fs %s/lib/* %s/lib; fi" % (remote_repository_dir, remote_repository_dir, home_path))):
            global_ret = False
            stdio.error('fail to init %s home path', server)
            
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')