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
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import absolute_import, division, print_function

import os
import re
import subprocess

from ssh import LocalClient

stdio = None


def parse_size(size):
    _bytes = 0
    if not isinstance(size, str) or size.isdigit():
        _bytes = int(size)
    else:
        units = {"B": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}
        match = re.match(r'(0|[1-9][0-9]*)\s*([B,K,M,G,T])', size.upper())
        _bytes = int(match.group(1)) * units[match.group(2)]
    return _bytes


def format_size(size, precision=1):
    units = ['B', 'K', 'M', 'G']
    units_num = len(units) - 1
    idx = 0
    if precision:
        div = 1024.0
        format = '%.' + str(precision) + 'f%s'
        limit = 1024
    else:
        div = 1024
        limit = 1024
        format = '%d%s'
    while idx < units_num and size >= limit:
        size /= div
        idx += 1
    return format % (size, units[idx])


def pre_test(plugin_context, cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    def execute(cursor, query, args=None):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose('execute sql: %s' % msg)
        # stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            cursor.execute(query, args)
            return cursor.fetchone()
        except:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    global stdio
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    options = plugin_context.options

    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
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

    ret = LocalClient.execute_command('%s --help' % obclient_bin, stdio=stdio)
    if not ret:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (
            ret.stderr, obclient_bin))
        return
    ret = LocalClient.execute_command('%s --help' % sysbench_bin, stdio=stdio)
    if not ret:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--sysbench-bin` to set.\nYou may not have ob-sysbench installed' % (
            ret.stderr, sysbench_bin))
        return

    if not script_name.endswith('.lua'):
        script_name += '.lua'
    script_path = os.path.join(sysbench_script_dir, script_name)
    if not os.path.exists(script_path):
        stdio.error(
            'No such file %s. Please use `--sysbench-script-dir` to set sysbench scrpit dir.\nYou may not have ob-sysbench installed' % script_path)
        return

    sql = "select * from oceanbase.gv$tenant where tenant_name = %s"
    try:
        stdio.verbose('execute sql: %s' % (sql % tenant_name))
        cursor.execute(sql, [tenant_name])
        tenant_meta = cursor.fetchone()
        if not tenant_meta:
            stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
            return
        sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d" % tenant_meta['tenant_id']
        pool = execute(cursor, sql)
        sql = "select * from oceanbase.__all_unit_config where unit_config_id = %d" % pool['unit_config_id']
        max_cpu = execute(cursor, sql)['max_cpu']
    except:
        stdio.exception('')
        return

    exec_sql_cmd = "%s -h%s -P%s -u%s@%s %s -A -e" % (
    obclient_bin, host, port, user, tenant_name, ("-p'%s'" % password) if password else '')
    ret = LocalClient.execute_command('%s "%s"' % (exec_sql_cmd, 'create database if not exists %s;' % mysql_db),
                                      stdio=stdio)
    if not ret:
        stdio.error(ret.stderr)
        return
    server_num = len(cluster_config.servers)
    sql = "select count(1) server_num from oceanbase.__all_server where status = 'active'"
    ret = execute(cursor, sql)
    if ret:
        server_num = ret.get("server_num", server_num)
    return plugin_context.return_true(
        max_cpu=max_cpu, threads=threads, parse_size=parse_size, tenant=tenant_name, tenant_id=tenant_meta['tenant_id'],
        format_size=format_size, server_num=server_num, obclient_bin=obclient_bin, host=host, port=port, user=user,
        password=password, database=mysql_db
    )