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

import re

import _errno as err


def password_check(password):
    if not re.match(r'^[\w~^*{}\[\]_\-+]+$', password):
        return False
    return True


def http_basic_auth_password_check(plugin_context, start_check_status, **kwargs):
    critical = plugin_context.get_variable('check_fail')
    env = plugin_context.get_variable('start_env')
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.verbose('http_basic_auth_password check')

    for server in cluster_config.servers:
        server_config = env[server]

        # http_basic_auth_password check
        http_basic_auth_password = server_config.get('http_basic_auth_password')
        if http_basic_auth_password:
            if not password_check(http_basic_auth_password):
                critical(server, 'password', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='obagent', key='http_basic_auth_password', rule='^[\w~^*{}\[\]_\-+]+$'), suggests=[err.SUG_OBAGENT_EDIT_HTTP_BASIC_AUTH_PASSWORD.format()])
    return plugin_context.return_true()