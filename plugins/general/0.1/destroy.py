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