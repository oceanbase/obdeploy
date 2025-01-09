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


def stop_pre(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    servers_pid_filenames = {}
    for server in cluster_config.servers:
        servers_pid_filenames[server] = ['prometheusd.pid', 'prometheus.pid']
    plugin_context.set_variable('servers_pid_filenames', servers_pid_filenames)
    plugin_context.set_variable('port_keys', ['port'])

    return plugin_context.return_true()
