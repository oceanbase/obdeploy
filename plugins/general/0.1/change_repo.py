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



def change_repo(plugin_context, local_home_path, repository, *args, **kwargs):
    components = plugin_context.components
    cluster_config = plugin_context.cluster_config
    repository_dir = repository.repository_dir
    options = plugin_context.options
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    global_ret = True

    stdio.start_loading('Change repository')
    for server in cluster_config.servers:
        client = clients[server]
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        remote_home_path = client.execute_command('echo ${OBD_HOME:-"$HOME"}/.obd').stdout.strip()
        remote_repository_dir = repository_dir.replace(local_home_path, remote_home_path)
        global_ret = client.execute_command("bash -c 'mkdir -p %s/{bin,lib}'" % (home_path)) and global_ret
        global_ret = client.execute_command("ln -fs %s/bin/* %s/bin" % (remote_repository_dir, home_path)) and global_ret
        global_ret = client.execute_command("ln -fs %s/lib/* %s/lib" % (remote_repository_dir, home_path)) and global_ret
    
    if global_ret:
        stdio.stop_loading('succeed')
        plugin_context.return_true()
    else:
        stdio.stop_loading('failed')