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
        stdio.error('当前插件版本不支持 OCP V%s' % ocp_version)
        return

    if ocp_version > max_version:
        stdio.warn('OCP V%s 高于当前插件库支持版本，接管要求可能与本次检查不符' % ocp_version)

    for server in cluster_config.servers:
        client = clients[server]
        if is_admin and client.config.username != 'admin':
            is_admin = False
            stdio.error('用户必须是admin用户。请使用edit-config修改user.username字段修改')
        if can_sudo and not client.execute_command('sudo whoami'):
            can_sudo = False
            stdio.error('用户需要sudo免密权限')
        if not client.execute_command('bash -c "if [ `pgrep obproxy | wc -l` -gt 1 ]; then exit 1; else exit 0;fi;"'):
            only_one = False
            stdio.error('%s 存在多个 obproxy' % server)

    if is_admin and can_sudo and only_one:
        stdio.print('当前 obproxy 的配置生效后可以被ocp接管' if new_cluster_config else '当前 obproxy 的配置可以被ocp接管')
        return plugin_context.return_true()