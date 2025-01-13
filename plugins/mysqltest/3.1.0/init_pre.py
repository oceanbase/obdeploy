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
