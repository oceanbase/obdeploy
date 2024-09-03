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

import os.path

from _errno import EC_FAIL_TO_INIT_PATH, InitDirFailedErrorMessage, EC_COMPONENT_DIR_NOT_EMPTY


def check_home_path(home_path, client):
    """
    Check if home_path exists
    """
    return client.execute_command('ls -d {0} 2>/dev/null'.format(home_path))


def kill_pid(home_path, client):
    """
    pkill the pid ,no return
    """
    client.execute_command("pkill -9 -u `whoami` -f '{}'".format(os.path.join(home_path, 'bin/ob-configserver')))


def clean_home_path(home_path, client):
    """
    clean home_path
    """
    return client.execute_command('rm -fr %s' % home_path, timeout=-1)


def init(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    stdio.start_loading('Initializes ob-configserver work home')

    if len(cluster_config.servers) > 1:
        stdio.warn('There are multiple servers configured for ob-configserver, only the first one will depended by oceanbase')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        home_path = server_config['home_path']

        home_path_exist = check_home_path(home_path, client)
        if home_path_exist:
            if force:
                kill_pid(home_path, client)
                ret = clean_home_path(home_path, client)
                if not ret:
                    global_ret = False
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
            else:
                global_ret = False
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=home_path)))
                stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)

        if global_ret and not client.execute_command(f"""bash -c 'mkdir -p {os.path.join(home_path, '{run,bin,conf,log}')}'"""):
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path',msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path)))
            global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
