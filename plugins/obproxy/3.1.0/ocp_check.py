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

from _rpm import Version


def ocp_check(plugin_context, ocp_version, cursor, new_cluster_config=None, new_clients=None, *args, **kwargs):
    cluster_config = new_cluster_config if new_cluster_config else plugin_context.cluster_config
    clients = new_clients if new_clients else plugin_context.clients
    stdio = plugin_context.stdio
    
    is_admin = True
    can_sudo = True
    only_one = True
    
    min_version = Version('3.1.1')
    max_version = min_version
    ocp_version = Version(ocp_version)

    if ocp_version < min_version:
        stdio.error('The current plugin version does not support OCP V%s' % ocp_version)
        return

    if ocp_version > max_version:
        stdio.warn('The plugin library does not support OCP V%s. The takeover requirements are not applicable to the current check.' % ocp_version)

    for server in cluster_config.servers:
        client = clients[server]
        if is_admin and client.config.username != 'admin':
            is_admin = False
            stdio.error('The current user must be the admin user. Run the edit-config command to modify the user.username field')
        if can_sudo and not client.execute_command('sudo whoami'):
            can_sudo = False
            stdio.error('The user must have the privilege to run sudo commands without a password.')
        if not client.execute_command('bash -c "if [ `pgrep obproxy | wc -l` -gt 1 ]; then exit 1; else exit 0;fi;"'):
            only_one = False
            stdio.error('%s Multiple OBProxies exist.' % server)

    if is_admin and can_sudo and only_one:
        stdio.print('Configurations of the OBProxy can be taken over by OCP after they take effect.' if new_cluster_config else 'Configurations of the OBProxy can be taken over by OCP.')
        return plugin_context.return_true()