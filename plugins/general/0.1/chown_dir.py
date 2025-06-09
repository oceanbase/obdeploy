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
                if cluster_config.name in const.COMPS_OCP:
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
            chown_dir_flags = False
        dir_read_check(new_client, server_config['home_path'])

    return plugin_context.return_true()
