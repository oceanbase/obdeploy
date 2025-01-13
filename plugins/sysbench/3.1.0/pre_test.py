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

import os
import subprocess

from ssh import LocalClient
from _types import Capacity
from const import TOOL_SYSBENCH, COMP_OBCLIENT

stdio = None

def file_path_check(bin_path, tool_name, tool_path, cmd):
    result = None
    tool_path = os.path.join(os.getenv('HOME'), tool_name, tool_path)
    for path in [bin_path, tool_path]:
        result = LocalClient.execute_command(cmd % path, stdio=stdio)
        if not result:
            continue
        break
    else:
        return None, result
    return path, None


def pre_test(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    global stdio
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options

    sys_namespace = kwargs.get("sys_namespace")
    get_db_and_cursor = kwargs.get("get_db_and_cursor")
    db, cursor = get_db_and_cursor(sys_namespace)

    host = get_option('host', '127.0.0.1')
    port = db.port if db else 2881
    mysql_db = get_option('database', 'test')
    user = get_option('user', 'root')
    tenant_name = get_option('tenant', 'test')
    password = get_option('password', '')
    threads = get_option('threads', 150)
    script_name = get_option('script_name', 'oltp_point_select.lua')
    obclient_bin = get_option('obclient_bin', 'obclient')
    sysbench_bin = get_option('sysbench_bin', 'sysbench')
    sysbench_script_dir = get_option('sysbench_script_dir', '/usr/sysbench/share/sysbench')

    if tenant_name == 'sys':
        stdio.error('DO NOT use sys tenant for testing.')
        return

    cmd = '%s --help'
    path, result = file_path_check(obclient_bin, COMP_OBCLIENT, 'bin/obclient', cmd)
    if result:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (
                result.stderr, obclient_bin))
        return
    obclient_bin = path
    setattr(options, 'obclient_bin', obclient_bin)

    path, result = file_path_check(sysbench_bin, TOOL_SYSBENCH, 'sysbench/bin/sysbench', cmd)
    if result:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--sysbench-bin` to set.\nYou may not have ob-sysbench installed' % (
                result.stderr, sysbench_bin))
        return
    setattr(options, 'sysbench_bin', path)

    if not os.path.exists(sysbench_script_dir):
        sysbench_script_dir = os.path.join(os.getenv('HOME'), TOOL_SYSBENCH, 'sysbench/share/sysbench')
        setattr(options, 'sysbench_script_dir', sysbench_script_dir)

    scripts = script_name.split(',')
    for script in scripts:
        if not script.endswith('.lua'):
            script += '.lua'
        script_path = os.path.join(sysbench_script_dir, script)
        if not os.path.exists(script_path):
            stdio.error(
                'No such file %s. Please use `--sysbench-script-dir` to set sysbench scrpit dir.\nYou may not have ob-sysbench installed' % script_path)
            return

    for thread in threads.split(","):
        if not thread.isdecimal():
            stdio.error("Illegal characters in threads: %s" % thread)
            return

    query_tenant_sql = plugin_context.get_variable("tenant_sql")
    stdio.verbose('execute sql: %s' % (query_tenant_sql % tenant_name))
    tenant_meta = cursor.fetchone(query_tenant_sql, [tenant_name])
    if not tenant_meta:
        stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
        return
    tenant_id = plugin_context.get_variable("tenant_id")
    sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d" % tenant_meta[tenant_id]
    pool = cursor.fetchone(sql)
    if pool is False:
        return
    sql = "select * from oceanbase.__all_unit_config where unit_config_id = %d" % pool['unit_config_id']
    max_cpu = cursor.fetchone(sql)
    if max_cpu is False:
        return
    max_cpu = max_cpu['max_cpu']

    exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A -e" % (
    obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '')
    ret = LocalClient.execute_command('%s "%s"' % (exec_sql_cmd, 'create database if not exists %s;' % mysql_db),
                                      stdio=stdio)
    if not ret:
        stdio.error(ret.stderr)
        return
    server_num = len(cluster_config.servers)
    sql = "select count(1) server_num from oceanbase.__all_server where status = 'active'"
    ret = cursor.fetchone(sql)
    if ret is False:
        return
    if ret:
        server_num = ret.get("server_num", server_num)
    return plugin_context.return_true(
        max_cpu=max_cpu, threads=threads, Capacity=Capacity, tenant=tenant_name, tenant_id=tenant_meta[tenant_id],
        format_size=Capacity, server_num=server_num, obclient_bin=obclient_bin, host=host, port=port, user=user,
        password=password, database=mysql_db
    )