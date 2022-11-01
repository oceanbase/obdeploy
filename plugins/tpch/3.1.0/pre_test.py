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


import re
import os
from glob import glob
try:
    import subprocess32 as subprocess
except:
    import subprocess
from ssh import LocalClient
from tool import DirectoryUtil


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
        if not value:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def get_path(key, default):
        path = get_option('%s_path' % key)
        if path and os.path.exists(path):
            if os.path.isfile(path):
                path = [path]
            else:
                path = glob(os.path.join(path, '*.%s' % key))
        stdio.verbose('get %s_path: %s' % (key, path))
        return path if path else default

    def execute(cursor, query, args=None):
        msg = query % tuple(args) if args is not None else query
        stdio.verbose('execute sql: %s' % msg)
        stdio.verbose("query: %s. args: %s" % (query, args))
        try:
            cursor.execute(query, args)
            return cursor.fetchone()
        except:
            msg = 'execute sql exception: %s' % msg
            stdio.exception(msg)
            raise Exception(msg)

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    options = plugin_context.options
    clients = plugin_context.clients

    local_dir, _ = os.path.split(__file__)
    dbgen_bin = get_option('dbgen_bin', 'dbgen')
    dss_config = get_option('dss_config', '.')
    scale_factor = get_option('scale_factor', 1)
    disable_transfer = get_option('disable_transfer', False)
    remote_tbl_dir = get_option('remote_tbl_dir')
    tenant_name = get_option('tenant', 'test')
    host = get_option('host', '127.0.0.1')
    port = get_option('port', 2881)
    mysql_db = get_option('database', 'test')
    user = get_option('user', 'root')
    password = get_option('password', '')

    if tenant_name == 'sys':
        stdio.error('DO NOT use sys tenant for testing.')
        return 

    test_server = get_option('test_server')
    tmp_dir = os.path.abspath(get_option('tmp_dir', './tmp'))
    tbl_tmp_dir = os.path.join(tmp_dir, 's%s' % scale_factor)
    ddl_path = get_path('ddl', [os.path.join(local_dir, 'create_tpch_mysql_table_part.ddl')])
    stdio.verbose('set ddl_path: %s' % ddl_path)
    setattr(options, 'ddl_path', ddl_path)
    tbl_path = get_path('tbl', glob(os.path.join(tbl_tmp_dir, '*.tbl')))
    sql_path = get_path('sql', glob(os.path.join(local_dir, 'queries/*.sql')))
    stdio.verbose('set sql_path: %s' % sql_path)
    setattr(options, 'sql_path', sql_path)
    obclient_bin = get_option('obclient_bin', 'obclient')

    ret = local_execute_command('%s --help' % obclient_bin)
    if not ret:
        stdio.error('%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (ret.stderr, obclient_bin))
        return

    if not DirectoryUtil.mkdir(tmp_dir, stdio=stdio):
        return
    stdio.verbose('set tmp_dir: %s' % tmp_dir)
    setattr(options, 'tmp_dir', tmp_dir)

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
        tenant_unit = execute(cursor, sql)
        max_cpu = tenant_unit['max_cpu']
        min_memory = tenant_unit['min_memory']
        unit_count = pool['unit_count']
    except:
        stdio.error('fail to get tenant info')
        return
    server_num = len(cluster_config.servers)
    sql = "select count(1) server_num from oceanbase.__all_server where status = 'active'"
    ret = execute(cursor, sql)
    if ret:
        server_num = ret.get("server_num", server_num)

    if get_option('test_only'):
        return plugin_context.return_true(
            max_cpu=max_cpu, min_memory=min_memory, unit_count=unit_count, server_num=server_num, tenant=tenant_name,
            tenant_id=tenant_meta['tenant_id'], format_size=format_size
        )

    if not remote_tbl_dir:
        stdio.error('Please use --remote-tbl-dir to set a dir for remote tbl files')
        return
    
    if disable_transfer:
        ret = clients[test_server].execute_command('ls %s' % (os.path.join(remote_tbl_dir, '*.tbl')))
        tbl_path = ret.stdout.strip().split('\n') if ret else []
        if not tbl_path:
            stdio.error('No tbl file in %s:%s' % (test_server, remote_tbl_dir))
            return
    else:
        if not tbl_path:
            ret = local_execute_command('%s -h' % dbgen_bin)
            if ret.code > 1:
                stdio.error('%s\n%s is not an executable file. Please use `--dbgen-bin` to set.\nYou may not have obtpch installed' % (ret.stderr, dbgen_bin))
                return
            
            dss_path = os.path.join(dss_config, 'dists.dss')
            if not os.path.exists(dss_path):
                stdio.error('No such file: %s' % dss_path)
                return

            tbl_tmp_dir = os.path.join(tmp_dir, 's%s' % scale_factor)
            if not DirectoryUtil.mkdir(tbl_tmp_dir, stdio=stdio):
                return

            stdio.start_loading('Generate Data (Scale Factor: %s)' % scale_factor)
            ret = local_execute_command('cd %s; %s -s %s -b %s' % (tbl_tmp_dir, dbgen_bin, scale_factor, dss_path))
            if ret:
                stdio.stop_loading('succeed')
                tbl_path = glob(os.path.join(tbl_tmp_dir, '*.tbl'))
            else:
                stdio.stop_loading('fail')
                return

        stdio.start_loading('Send tbl to remote (%s)' % test_server)
        new_tbl_path = []
        for path in tbl_path:
            _, fn = os.path.split(path)
            fp = os.path.join(remote_tbl_dir, fn)
            if not clients[test_server].put_file(path, fp):
                stdio.stop_loading('fail')
                return

            new_tbl_path.append(fp)
        tbl_path = new_tbl_path

    stdio.stop_loading('succeed')
    stdio.verbose('set tbl_path: %s' % tbl_path)
    setattr(options, 'tbl_path', tbl_path)

    return plugin_context.return_true(
        obclient_bin=obclient_bin, host=host, port=port, user=user, password=password, database=mysql_db,
        max_cpu=max_cpu, min_memory=min_memory, unit_count=unit_count, server_num=server_num, tenant=tenant_name,
        tenant_id=tenant_meta['tenant_id'], format_size=format_size
    )


