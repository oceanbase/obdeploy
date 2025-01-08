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


def password_regular_check(passwd):
    pattern = r'''^(?=(.*[a-z]){2,})(?=(.*[A-Z]){2,})(?=(.*\d){2,})(?=(.*[~!@#%^&*_\-+=|(){}\[\]:;,.?/]){2,})[A-Za-z\d~!@#%^&*_\-+=|(){}\[\]:;,.?/]{8,32}$'''
    return True if re.match(pattern, passwd) else False


def password_check(plugin_context, **kwargs):
    error = plugin_context.get_variable('error')
    env = plugin_context.get_variable('start_env')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    stdio.verbose('admin_password check')
    # admin_passwd check
    for server in cluster_config.servers:
        server_config = env[server]
        admin_passwd = server_config.get('admin_passwd')
        if not admin_passwd or not password_regular_check(admin_passwd):
            error(server, 'admin_passwd', err.EC_COMPONENT_PASSWD_ERROR.format(ip=server.ip, component='ocp-express', key='admin_passwd', rule='The password must be 8 to 32 characters in length, containing at least 2 uppercase letters, 2 lowercase letters, 2 numbers, and 2 of the following special characters: ~!@#%^&*_-+=|(){{}}[]:;,.?/'), suggests=[err.SUG_OCP_EXPRESS_EDIT_ADMIN_PASSWD.format()])
    return plugin_context.return_true()