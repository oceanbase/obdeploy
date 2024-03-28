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
import subprocess

from ssh import LocalClient
from _types import Capacity

stdio = None


def pre_test(plugin_context, cursor, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    global stdio
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
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

    sql = "select * from oceanbase.DBA_OB_TENANTS where TENANT_NAME = %s"
    max_cpu = 2
    tenant_meta = None
    stdio.verbose('execute sql: %s' % (sql % tenant_name))
    tenant_meta = cursor.fetchone(sql, [tenant_name])
    if not tenant_meta:
        stdio.error('Tenant %s not exists. Use `obd cluster tenant create` to create tenant.' % tenant_name)
        return
    sql = "select * from oceanbase.__all_resource_pool where tenant_id = %d" % tenant_meta['TENANT_ID']
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
        max_cpu=max_cpu, threads=threads, Capacity=Capacity, tenant=tenant_name, tenant_id=tenant_meta['TENANT_ID'],
        format_size=Capacity, server_num=server_num, obclient_bin=obclient_bin, host=host, port=port, user=user,
        password=password, database=mysql_db
    )