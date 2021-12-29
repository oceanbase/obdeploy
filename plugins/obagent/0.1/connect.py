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


def connect(plugin_context, target_server=None, *args, **kwargs):
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    servers = cluster_config.servers
    result = {}
    for server in servers:
        config = cluster_config.get_server_conf_with_default(server)
        if config.get('disable_http_basic_auth'):
            auth = ''
        else:
            auth = '--user %s:%s' % (config['http_basic_auth_user'], config['http_basic_auth_password'])
        cmd = '''curl %s -H "Content-Type:application/json" -L "http://%s:%s/metrics/stat"''' % (auth, server.ip, config['server_port'])
        result[server] = cmd
    return plugin_context.return_true(connect=result, cursor=result)
