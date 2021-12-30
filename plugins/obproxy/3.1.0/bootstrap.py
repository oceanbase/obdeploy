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


def bootstrap(plugin_context, cursor, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global_ret = True
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        for key in ['observer_sys_password', 'obproxy_sys_password']:
            sql = 'alter proxyconfig set %s = %%s' % key
            value = None
            try:
                value = server_config.get(key, '')
                value = '' if value is None else str(value)
                stdio.verbose('execute sql: %s' % (sql % value))
                cursor[server].execute(sql, [value])
            except:
                stdio.exception('execute sql exception: %s' % (sql % (value)))
                stdio.error('failed to set %s for obproxy(%s)' % (key, server))
                global_ret = False
    if global_ret:
        plugin_context.return_true()
    else:
        plugin_context.return_false()
