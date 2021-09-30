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


def pre_test(plugin_context, *args, **kwargs):
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

    if get_option('test_only'):
        return plugin_context.return_true()

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
    return plugin_context.return_true()


