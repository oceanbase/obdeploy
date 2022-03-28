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
import os
from ssh import LocalClient

from _errno import EC_MYSQLTEST_FAILE_NOT_FOUND, EC_MYSQLTEST_PARSE_CMD_FAILED


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1<<10, "M": 1<<20, "G": 1<<30, "T": 1<<40}
        match = re.match(r'([1-9][0-9]*)\s*([B,K,M,G,T])', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def get_memory_limit(cursor, client):
    try:
        cursor.execute('show parameters where name = \'memory_limit\'')
        memory_limit = cursor.fetchone()
        if memory_limit and 'value' in memory_limit and memory_limit['value']:
            return parse_size(memory_limit['value'])
        ret = client.execute_command('free -b')
        if ret:
            ret = client.execute_command("cat /proc/meminfo | grep 'MemTotal:' | awk -F' ' '{print $2}'")
            total_memory = int(ret.stdout) * 1024
            cursor.execute('show parameters where name = \'memory_limit_percentage\'')
            memory_limit_percentage = cursor.fetchone()
            if memory_limit_percentage and 'value' in memory_limit_percentage and memory_limit_percentage['value']:
                total_memory = total_memory * memory_limit_percentage['value'] / 100
            return total_memory
    except:
        pass
    return 0


def get_root_server(cursor):
    try:
        cursor.execute('select * from oceanbase.__all_server where status = \'active\' and with_rootserver=1')
        return cursor.fetchone()
    except:
        pass
    return None


def init(plugin_context, env, *args, **kwargs):
    def exec_sql(cmd):
        ret = re.match('(.*\.sql)(?:\|([^\|]*))?(?:\|([^\|]*))?', cmd)
        if not ret:
            stdio.error(EC_MYSQLTEST_PARSE_CMD_FAILED.format(path=cmd))
            return False
        cmd = ret.groups()
        sql_file_path1 = os.path.join(init_sql_dir, cmd[0])
        sql_file_path2 = os.path.join(plugin_init_sql_dir, cmd[0])
        if os.path.isfile(sql_file_path1):
            sql_file_path = sql_file_path1
        elif os.path.isfile(sql_file_path2):
            sql_file_path = sql_file_path2
        else:
            stdio.error(EC_MYSQLTEST_FAILE_NOT_FOUND.format(file=cmd[0], path='[%s, %s]' % (init_sql_dir, plugin_init_sql_dir)))
            return False
        exec_sql_cmd = exec_sql_temp % (cmd[1] if cmd[1] else 'root', cmd[2] if cmd[2] else 'oceanbase', sql_file_path)
        ret = LocalClient.execute_command(exec_sql_cmd, stdio=stdio)
        if ret:
            return True
        stdio.error('Failed to Excute %s: %s' % (sql_file_path, ret.stderr.strip()))
        return False
        
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    cursor = env['cursor']
    obclient_bin = env['obclient_bin']
    mysqltest_bin = env['mysqltest_bin']
    server = env['test_server']
    root_server = get_root_server(cursor)
    if root_server:
        port = root_server['inner_port']
        host = root_server['svr_ip']
    else:
        stdio.error('Failed to get root server.')
        return plugin_context.return_false()
    init_sql_dir = env['init_sql_dir']
    plugin_init_sql_dir = os.path.join(os.path.split(__file__)[0], 'init_sql')
    exec_sql_temp = obclient_bin + ' --prompt "OceanBase(\\u@\d)>" -h ' + host + ' -P ' + str(port) + ' -u%s -D%s -c < %s'

    if 'init_sql_files' in env and env['init_sql_files']:
        init_sql = env['init_sql_files'].split(',')
    else:
        exec_init = 'init.sql'
        exec_mini_init = 'init_mini.sql'
        exec_init_user = 'init_user.sql|root@mysql|test'
        client = plugin_context.clients[server]
        memory_limit = get_memory_limit(cursor, client)
        is_mini = memory_limit and parse_size(memory_limit) < (16<<30)
        if is_mini:
            init_sql = [exec_mini_init, exec_init_user]
        else:
            init_sql = [exec_init, exec_init_user]

    stdio.start_loading('Execute initialize sql')
    for sql in init_sql:
        if not exec_sql(sql):
            stdio.stop_loading('fail')
            return plugin_context.return_false()
    stdio.stop_loading('succeed')
    return plugin_context.return_true()
