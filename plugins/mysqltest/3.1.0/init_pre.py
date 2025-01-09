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

from _types import Capacity


def get_memory_limit(cursor, client):
    try:
        memory_limit = cursor.fetchone('show parameters where name = \'memory_limit\'')
        if memory_limit and 'value' in memory_limit and memory_limit['value']:
            return Capacity(memory_limit['value']).bytes
        ret = client.execute_command('free -b')
        if ret:
            ret = client.execute_command("cat /proc/meminfo | grep 'MemTotal:' | awk -F' ' '{print $2}'")
            total_memory = int(ret.stdout) * 1024
            memory_limit_percentage = cursor.fetchone('show parameters where name = \'memory_limit_percentage\'')
            if memory_limit_percentage and 'value' in memory_limit_percentage and memory_limit_percentage['value']:
                total_memory = total_memory * memory_limit_percentage['value'] / 100
            return total_memory
    except:
        pass
    return 0


def init_pre(plugin_context, env, *args, **kwargs):
    server = env['test_server']
    cursor = plugin_context.get_return('connect').get_return('cursor')
    if 'init_sql_files' in env and env['init_sql_files']:
        init_sql = env['init_sql_files'].split(',')
    else:
        exec_init = 'init.sql'
        exec_mini_init = 'init_mini.sql'
        exec_init_user = 'init_user.sql|root@mysql|test'
        exec_init_user_for_oracle = 'init_user_oracle.sql|SYS@oracle|SYS'
        client = plugin_context.clients[server]
        memory_limit = get_memory_limit(cursor, client)
        is_mini = memory_limit and Capacity(memory_limit).bytes < (16 << 30)
        if env['is_business']:
            init_sql = [exec_mini_init if is_mini else exec_init, exec_init_user_for_oracle, exec_init_user]
        else:
            init_sql = [exec_mini_init if is_mini else exec_init, exec_init_user]

    plugin_context.set_variable('init_sql', init_sql)
    return plugin_context.return_true()
