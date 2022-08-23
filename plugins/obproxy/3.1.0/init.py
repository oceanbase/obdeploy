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

from _errno import EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage


def init(plugin_context, local_home_path, repository_dir, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    clean = getattr(plugin_context.options, 'clean', False)
    stdio.start_loading('Initializes obproxy work home')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']
        remote_home_path = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
        remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
        stdio.verbose('%s init cluster work home', server)
        need_clean = force
        if clean and not force:
            if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
                owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
                global_ret = False
                err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
                continue
            need_clean = True

        if need_clean:
            client.execute_command("pkill -9 -u `whoami` -f '^bash {home_path}/obproxyd.sh {home_path} {ip} {port} daemon$'".format(home_path=home_path, ip=server.ip, port=server_config.get('listen_port')))
            client.execute_command("pkill -9 -u `whoami` -f '^%s/bin/obproxy --listen_port %s'" % (home_path, server_config.get('listen_port')))
            ret = client.execute_command('rm -fr %s' % home_path)
            if not ret:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
                continue
        if not client.execute_command("bash -c 'mkdir -p %s/{run,bin,lib}'" % home_path):
            global_ret = False
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
            
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('fail')