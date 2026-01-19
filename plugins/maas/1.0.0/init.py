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
from tool import get_sudo_prefix


def check_mount_path(mount_path, client):
    """
    Check if mount_path exists
    """
    ret = client.execute_command('ls -A {0} 2>/dev/null'.format(mount_path))
    if not ret or not ret.stdout.strip():
        return False
    else:
        return True

def clean_mount_path(mount_path, client):
    """
    clean mount_path
    """
    return client.execute_command(f'rm -fr %s' % mount_path, timeout=-1)


def init(plugin_context, source_option=None, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio
    deploy_name = plugin_context.deploy_name
    global_ret = True
    force = getattr(plugin_context.options, 'force', False)
    stdio.start_loading('Initializes MAAS mount path')

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = clients[server]
        model_cache_path = server_config.get('model_cache_path')
        docker_image_path = server_config.get('docker_image_path')
        data_dir = server_config.get('data_dir')
        if not all([model_cache_path, docker_image_path, data_dir]):
            global_ret = False
            stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='model_cache_path,docker_image_path,data_dir', msg='is required'))
            continue

        need_init_paths = [model_cache_path, docker_image_path]
        for mount_path in need_init_paths:
            mount_path_exist = check_mount_path(mount_path, client)
            if mount_path_exist:
                if force:
                    ret = clean_mount_path(mount_path, client)
                    if not ret:
                        global_ret = False
                        stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='mount path', msg=ret.stderr))
                else:
                    global_ret = False
                    stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='mount path', msg=InitDirFailedErrorMessage.NOT_EMPTY.format(path=mount_path)))
                    source_option == "deploy" and stdio.error(EC_COMPONENT_DIR_NOT_EMPTY.format(deploy_name=deploy_name), _on_exit=True)

            if global_ret and not client.execute_command(f"""bash -c 'mkdir -p {os.path.join(mount_path)}'"""):
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='mount path',msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=mount_path)))
                global_ret = False

            can_access = client.execute_command(f"[ -r '{mount_path}' ] && [ -w '{mount_path}' ] && echo true || echo false").stdout.strip() == "true"
            if not can_access:
                stdio.error(EC_FAIL_TO_INIT_PATH.format(server=server, key='mount path',msg=InitDirFailedErrorMessage.PERMISSION_DENIED.format(path=mount_path)))
                global_ret = False

    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    stdio.stop_loading('fail')

