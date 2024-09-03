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
import time
import hashlib

from ssh import LocalClient
from tool import FileUtil
from _errno import EC_MYSQLTEST_FAILE_NOT_FOUND, EC_MYSQLTEST_PARSE_CMD_FAILED
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


def init(plugin_context, env, *args, **kwargs):
    def get_root_server(cursor):
        while True:
            try:
                return cursor.fetchone('select * from oceanbase.__all_server where status = \'active\' and with_rootserver=1', raise_exception=True)
            except:
                if load_snap:
                    time.sleep(0.1)
                    continue
            return None

    def exec_sql(cmd):
        ret = re.match('(.*\.sql)(?:\|([^\|]*))?(?:\|([^\|]*))?', cmd)
        if not ret:
            stdio.error(EC_MYSQLTEST_PARSE_CMD_FAILED.format(path=cmd))
            return None
        cmd = ret.groups()
        sql_file_path1 = os.path.join(init_sql_dir, cmd[0])
        sql_file_path2 = os.path.join(plugin_init_sql_dir, cmd[0])
        if os.path.isfile(sql_file_path1):
            sql_file_path = sql_file_path1
        elif os.path.isfile(sql_file_path2):
            sql_file_path = sql_file_path2
        else:
            stdio.error(EC_MYSQLTEST_FAILE_NOT_FOUND.format(file=cmd[0], path='[%s, %s]' % (init_sql_dir, plugin_init_sql_dir)))
            return None
        if load_snap:
            exec_sql_cmd = exec_sql_connect % (cmd[1] if cmd[1] else 'root')
        else:
            exec_sql_cmd = exec_sql_execute % (cmd[1] if cmd[1] else 'root', cmd[2] if cmd[2] else 'oceanbase', sql_file_path)
        
        while True:
            ret = LocalClient.execute_command(exec_sql_cmd, stdio=stdio)
            if ret:
                return sql_file_path
            if load_snap:
                time.sleep(0.1)
                continue
            stdio.error('Failed to Excute %s: %s' % (sql_file_path, ret.stderr.strip()))
            return None
        
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    load_snap = env.get('load_snap', False)
    cursor = env['cursor']
    obclient_bin = env['obclient_bin']
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
    exec_sql_execute = obclient_bin + ' --prompt "OceanBase(\\u@\d)>" -h ' + host + ' -P ' + str(port) + ' -u%s -D%s -c < %s'
    exec_sql_connect = obclient_bin + ' --prompt "OceanBase(\\u@\d)>" -h ' + host + ' -P ' + str(port) + ' -u%s -e "select 1 from DUAL"'

    if 'init_sql_files' in env and env['init_sql_files']:
        init_sql = env['init_sql_files'].split(',')
    else:
        exec_init = 'init.sql'
        exec_mini_init = 'init_mini.sql'
        exec_init_user = 'init_user.sql|root@mysql|test'
        exec_init_user_for_oracle = 'init_user_oracle.sql|SYS@oracle|SYS'
        client = plugin_context.clients[server]
        memory_limit = get_memory_limit(cursor, client)
        is_mini = memory_limit and Capacity(memory_limit).bytes < (16<<30)
        if env['is_business']:
            init_sql = [exec_mini_init if is_mini else exec_init, exec_init_user_for_oracle, exec_init_user]
        else:
            init_sql = [exec_mini_init if is_mini else exec_init, exec_init_user]

    m_sum = hashlib.md5() if not load_snap else None
    stdio.start_loading('Execute initialize sql')
    for sql in init_sql:
        sql_file_path = exec_sql(sql)
        if not sql_file_path:
            stdio.stop_loading('fail')
            return plugin_context.return_false()
        m_sum and m_sum.update(FileUtil.checksum(sql_file_path)) 
    stdio.stop_loading('succeed')

    if m_sum:
        env['init_file_md5'] = m_sum.hexdigest()
    return plugin_context.return_true()
