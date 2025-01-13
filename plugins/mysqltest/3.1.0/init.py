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
import os
import time
import hashlib

from ssh import LocalClient
from tool import FileUtil
from _errno import EC_MYSQLTEST_FAILE_NOT_FOUND, EC_MYSQLTEST_PARSE_CMD_FAILED
from _types import Capacity


def init(plugin_context, env=None, *args, **kwargs):
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

    stdio = plugin_context.stdio
    env = plugin_context.options.__dict__ if not env else env
    load_snap = env.get('load_snap', False)
    cursor = plugin_context.get_return('connect').get_return('cursor')
    obclient_bin = env['obclient_bin']
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

    init_sql = plugin_context.get_variable('init_sql')

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
    plugin_context.set_variable('env', env)
    return plugin_context.return_true()
