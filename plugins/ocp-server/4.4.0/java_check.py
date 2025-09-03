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
                    critical(server, 'java', err.EC_OCP_SERVER_JAVA_NOT_FOUND.format(server=server), [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='17')])
                version_pattern = r'version\s+\"(\d+\.\d+\.\d+)'
                found = re.search(version_pattern, ret.stdout) or re.search(version_pattern, ret.stderr)
                if not found:
                    error(server, 'java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='17'), [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='17'),])
                else:
                    java_major_version = found.group(1)
                    stdio.verbose('java_major_version %s' % java_major_version)
                    if Version(java_major_version) > Version('18') or Version(java_major_version) < Version('17'):
                        critical(server, 'java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='17'), [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='17'),])
        except Exception as e:
            stdio.error(e)
            error(server, 'java', err.EC_OCP_SERVER_JAVA_VERSION_ERROR.format(server=server, version='17'),
                  [err.SUG_OCP_SERVER_INSTALL_JAVA_WITH_VERSION.format(version='17'), ])
        check_pass(server, 'java')
    return plugin_context.return_true()