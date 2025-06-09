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


def init(plugin_context, source_option=None, *args, **kwargs):
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
                source_option == "deploy" and stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)

        if global_ret and not client.execute_command(f"""bash -c 'mkdir -p {os.path.join(home_path, '{run,bin,conf,log}')}'"""):
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path',msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=home_path)))
            global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')
