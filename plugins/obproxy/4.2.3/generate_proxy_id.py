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

import random


def generate_proxy_id(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    random_num = random.randint(1, 8191 - len(cluster_config.servers))
    num = 0
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client_session_id_version = server_config.get('client_session_id_version', 2)

        if client_session_id_version == 2:
            if server_config.get('proxy_id', None) is None:
                cluster_config.update_server_conf(server, 'proxy_id', random_num + num, False)
                cluster_config.update_server_conf(server, 'client_session_id_version', client_session_id_version, False)
            num += 1
    return plugin_context.return_true()