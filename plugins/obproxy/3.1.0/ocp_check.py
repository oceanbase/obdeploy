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

from _rpm import Version


def ocp_check(plugin_context, ocp_version, cursor, new_cluster_config=None, new_clients=None, *args, **kwargs):
    cluster_config = new_cluster_config if new_cluster_config else plugin_context.cluster_config
    clients = new_clients if new_clients else plugin_context.clients
    stdio = plugin_context.stdio
    
    is_admin = True
    can_sudo = True
    only_one = True
    
    min_version = Version('3.1.1')
    ocp_version_420 = Version("4.2.0")
    ocp_version = Version(ocp_version)

    if ocp_version < min_version:
        stdio.error('The current plugin version does not support OCP V%s' % ocp_version)
        return

    for server in cluster_config.servers:
        client = clients[server]
        if is_admin and client.config.username != 'admin' and ocp_version < ocp_version_420:
            is_admin = False
            stdio.error('The current user must be the admin user. Run the edit-config command to modify the user.username field')
        if can_sudo and not client.execute_command('sudo whoami'):
            can_sudo = False
            stdio.error('The user must have the privilege to run sudo commands without a password.')
        if not client.execute_command('bash -c "if [ `pgrep obproxy | wc -l` -gt 1 ]; then exit 1; else exit 0;fi;"'):
            only_one = False
            stdio.error('%s Multiple OBProxies exist.' % server)

    if (is_admin or ocp_version >= ocp_version_420) and can_sudo and only_one:
        stdio.print('Configurations of the OBProxy can be taken over by OCP after they take effect.' if new_cluster_config else 'Configurations of the OBProxy can be taken over by OCP.')
        return plugin_context.return_true()
