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

from tool import Cursor
import const


def init_schema(plugin_context, binlog_cursor=None, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        if not server_config.get('init_schema', True):
            stdio.verbose('skip init schema')
            return plugin_context.return_true()
    repositories = plugin_context.repositories
    repository = None
    for repo in repositories:
        if repo.name == const.COMP_OBBINLOG_CE:
            repository = repo

    depend_conf = plugin_context.get_variable('binlog_config')
    host  = depend_conf.get('database_ip')
    port  = depend_conf.get('database_port')
    username  = depend_conf.get('user')
    password  = depend_conf.get('password', '')
    db  = depend_conf.get('database_name')
    if not host or not port or not username or not db:
        stdio.error('one or more config(`meta_host`, `meta_port`, `meta_username`, `meta_password`, `meta_db`) is not set or not depends ob')
        return plugin_context.return_false()

    binlog_cursor = Cursor(host, port, username, tenant='', password=password, stdio=stdio)
    binlog_cursor.db.select_db(db)
    with open(repository.repository_dir + '/conf/schema.sql', 'r') as file:
        lines = file.readlines()
        sql = ''.join([line for line in lines if not (line.strip().startswith('#') or line.strip().startswith('--'))])
        sqls = sql.split(';\n')[:-1]

    for sql in sqls:
        binlog_cursor.execute(sql, raise_exception=True)
        binlog_cursor.db.commit()
    binlog_cursor = binlog_cursor.usable_cursor
    sql = "UPDATE %s.config_template SET value='false' WHERE key_name='enable_resource_check';" % db
    binlog_cursor.execute(sql)
    binlog_cursor.db.commit()
    return plugin_context.return_true()