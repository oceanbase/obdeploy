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

from _errno import EC_CLEAN_PATH_FAILED

global_ret = True

def check_mount_path(client, path, stdio):
    stdio and getattr(stdio, 'verbose', print)('check mount: %s' % path)
    try:
        if client.execute_command("grep '\\s%s\\s' /proc/mounts" % path):
            return True
        return False
    except Exception as e:
        stdio and getattr(stdio, 'exception', print)('')
        stdio and getattr(stdio, 'error', print)('failed to check mount: %s' % path)

def destroy(plugin_context, *args, **kwargs):
    def clean(server, path):
        client = clients[server]
        if check_mount_path(client, path, stdio):
            cmd = 'rm -fr %s/*' % path
        else:
            cmd = 'rm -fr %s' % path 
        ret = client.execute_command(sudo_command.get(server, "")+cmd, timeout=-1)
        if not ret:
            global global_ret
            global_ret = False
            stdio.warn(EC_CLEAN_PATH_FAILED.format(server=server, path=path))
        else:
            stdio.verbose('%s:%s cleaned' % (server, path))

    component_name = plugin_context.cluster_config.name
    clean_dirs = plugin_context.get_variable('clean_dirs', default=[])
    sudo_command = plugin_context.get_variable('sudo_command', default={})


    cluster_config = plugin_context.cluster_config
    clients = plugin_context.clients
    stdio = plugin_context.stdio

    stdio.start_loading('%s work dir cleaning' % component_name)
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        stdio.verbose('%s work path cleaning' % server)
        clean(server, server_config['home_path'])
        for key in clean_dirs:
            if server_config.get(key):
                clean(server, server_config[key])
                stdio.verbose('%s path cleaning ' % key)
    if global_ret:
        stdio.stop_loading('succeed')
        return plugin_context.return_true()
    else:
        stdio.stop_loading('fail')