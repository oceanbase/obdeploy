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
from _deploy import InnerConfigItem


def ocp_check(plugin_context, ocp_version, cursor, new_cluster_config=None, new_clients=None, *args, **kwargs):
    cluster_config = new_cluster_config if new_cluster_config else plugin_context.cluster_config
    clients = new_clients if new_clients else plugin_context.clients
    stdio = plugin_context.stdio
    
    is_admin = True
    can_sudo = True
    only_one = True
    pwd_not_empty = True

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
        if can_sudo and not (client.execute_command('[ `id -u` == "0" ]') or client.execute_command('sudo whoami')):
            can_sudo = False
            stdio.error('The user must have the privilege to run sudo commands without a password.')
        if not client.execute_command('bash -c "if [ `pgrep observer | wc -l` -gt 1 ]; then exit 1; else exit 0;fi;"'):
            only_one = False
            stdio.error('%s Multiple OBservers exist.' % server)

    try:
        if cursor.fetchone("select * from oceanbase.__all_user where user_name = 'root' and passwd = ''", raise_exception=True) and not cluster_config.get_global_conf().get("root_password"):
            pwd_not_empty = False
            stdio.error('The password of root@sys is empty. Run the edit-config command to modify the root_password value of %s.' % cluster_config.name)
    except:
        if not cluster_config.get_global_conf().get("root_password"):
            pwd_not_empty = False

    zones = {}
    try:
        ret = cursor.fetchall("select zone from oceanbase.__all_zone where name = 'idc' and info = ''", raise_exception=True)
        if ret:
            for row in ret:
                zones[str(row['zone'])] = 1
    finally:
        for server in cluster_config.servers:
            config = cluster_config.get_server_conf(server)
            zone = str(config.get('zone'))
            if zone in zones and config.get('$_zone_idc'):
                keys = list(config.keys())
                if '$_zone_idc' in keys and isinstance(keys[keys.index('$_zone_idc')], InnerConfigItem):
                    del zones[zone]
        if zones and ocp_version < ocp_version_420:
            if not cluster_config.parser or cluster_config.parser.STYLE == 'default':
                stdio.error('Zone: IDC information is missing for %s. Run the chst command to change the configuration style of %s to cluster, and then run the edit-config command to add IDC information.' % (','.join(zones.keys()), cluster_config.name))
            else:
                stdio.error('Zone: IDC information is missing for %s. Run the edit-config command to add IDC information.' % ','.join(zones.keys()))
        else:
            zones = {}

    # if ocp version is greater than 4.2.0, then admin and zone idc check is not needed
    if can_sudo and only_one and pwd_not_empty and is_admin and not zones:
        stdio.print('Configurations of the %s can be taken over by OCP after they take effect.' % cluster_config.name if new_cluster_config else 'Configurations of the %s can be taken over by OCP.' % cluster_config.name)
        return plugin_context.return_true()
