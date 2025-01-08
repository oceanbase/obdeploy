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

import time
import os

import const


def chown_dir(plugin_context, new_clients, *args, **kwargs):
    if not new_clients:
        return plugin_context.return_true()

    def dir_read_check(client, path):
        if not client.execute_command('cd %s' % path):
            dirpath, _ = os.path.split(path)
            return dir_read_check(client, dirpath) and client.execute_command('sudo chmod +1 %s' % path)
        return True

    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config

    dir_list = plugin_context.get_variable('dir_list', default=[])
    tmp_files = plugin_context.get_variable('tmp_files', default=[])
    stdio.verbose('use new clients')
    chown_dir_flags = False
    for server in cluster_config.servers:
        new_client = new_clients[server]
        server_config = cluster_config.get_server_conf(server)
        chown_cmd = 'sudo chown -R %s:' % new_client.config.username
        for key in dir_list:
            if key in server_config:
                chown_cmd += ' %s' % server_config[key]
                chown_dir_flags = True
        for file in tmp_files:
            if new_client.execute_command('[ -f {} ]'.format(file)):
                if cluster_config.name == const.COMP_OCP_SERVER_CE:
                    global_config = cluster_config.get_global_conf()
                    launch_user = global_config.get('launch_user')
                    if launch_user:
                        user = launch_user
                    else:
                        user = new_client.config.username
                    if chown_dir_flags:
                        chown_cmd += ';sudo  chown -R %s' % user
                    else:
                        chown_cmd = 'sudo chown -R %s' % user
                chown_cmd += ' %s' % file
                chown_dir_flags = True

        if chown_dir_flags:
            stdio.verbose('chown cmd: %s' % chown_cmd)
            if not new_client.execute_command(chown_cmd):
                stdio.stop_loading('stop_loading', 'fail')
                return False
        dir_read_check(new_client, server_config['home_path'])

    return plugin_context.return_true()
