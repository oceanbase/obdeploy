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
from _rpm import Version


def java_check(plugin_context, java_check=True, **kwargs):
    check_pass = plugin_context.get_variable('check_pass')
    critical = plugin_context.get_variable('critical')
    error = plugin_context.get_variable('critical')
    env = plugin_context.get_variable('start_env')

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    for server in cluster_config.servers:
        client = clients[server]
        server_config = env[server]
        try:
            # java version check
            if java_check:
                stdio.verbose('java check ')
                java_bin = server_config.get('java_bin', '/usr/bin/java')
                client.add_env('PATH', '%s/jre/bin:' % server_config['home_path'])
                ret = client.execute_command('{} -version'.format(java_bin))
                stdio.verbose('java version %s' % ret)
                if not ret:
                    critical(server, 'java', err.EC_OCP_SERVER_JAVA_NOT_FOUND.format(server=server), [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0')])
                version_pattern = r'version\s+\"(\d+\.\d+\.\d+)(\_\d+)'
                found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
                if not found:
                    error(server, 'java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
                else:
                    java_major_version = found.group(1)
                    stdio.verbose('java_major_version %s' % java_major_version)
                    java_update_version = found.group(2)[1:]
                    stdio.verbose('java_update_version %s' % java_update_version)
                    if Version(java_major_version) != Version('1.8.0') or int(java_update_version) < 161:
                        critical(server, 'java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'), [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'),])
        except Exception as e:
            stdio.error(e)
            error(server, 'java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='1.8.0'),
                  [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='1.8.0'), ])
        check_pass(server, 'java')
    return plugin_context.return_true()