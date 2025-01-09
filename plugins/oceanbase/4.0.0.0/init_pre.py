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


def init_pre(plugin_context, *args, **kwargs):
    data_dir_same_redo_dir_keys = ['home_path', 'data_dir', 'clog_dir', 'slog_dir']
    data_dir_not_same_redo_dir_keys = ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'slog_dir']
    clean_dir_keys = ['clog', 'slog']
    mkdir_keys = '{etc,admin,.conf,log,bin,lib}'

    dir_mapping = {
        'slog': 'data_dir',
        'clog': 'redo_dir',
    }

    def ob_clean(*args, **kwargs):
        pass

    def stop_ob_or_obshell(client=None, home_path=None, server_config=None, server=None, critical=None, EC_FAIL_TO_INIT_PATH=None, *args, **kwargs):
        res = []
        client.execute_command(
                "pkill -9 -u `whoami` -f '^%s/bin/observer -p %s'" % (home_path, server_config['mysql_port']))
        ret = client.execute_command('rm -fr %s/*' % home_path, timeout=-1)
        if not ret:
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=ret.stderr))
            res.append(False)
        return res

    def rm_meta(*args, **kwargs):
        pass

    def same_disk_check(stdio, client, server_config, critical, EC_FAIL_TO_INIT_PATH, server, *args, **kwargs):
        stdio.verbose("check slog dir in the same disk with data dir")
        slog_disk = data_disk = None
        ret = client.execute_command("df --block-size=1024 %s | awk 'NR == 2 { print $1 }'" % server_config['slog_dir'])
        if ret:
            slog_disk = ret.stdout.strip()
            stdio.verbose('slog disk is {}'.format(slog_disk))
        ret = client.execute_command("df --block-size=1024 %s | awk 'NR == 2 { print $1 }'" % server_config['data_dir'])
        if ret:
            data_disk = ret.stdout.strip()
            stdio.verbose('data disk is {}'.format(data_disk))
        if slog_disk != data_disk:
            critical(EC_FAIL_TO_INIT_PATH.format(
                server=server, key='slog dir',
                msg=': slog and data should be on the same disk. Now the slog disk is {slog_disk}, and the data disk is {data_disk}.'.format(slog_disk=slog_disk, data_disk=data_disk)))

    plugin_context.set_variable('same_disk_check', same_disk_check)
    plugin_context.set_variable('ob_clean', ob_clean)
    plugin_context.set_variable('dir_mapping', dir_mapping)
    plugin_context.set_variable('clean_dir_keys', clean_dir_keys)
    plugin_context.set_variable('data_dir_not_same_redo_dir_keys', data_dir_not_same_redo_dir_keys)
    plugin_context.set_variable('data_dir_same_redo_dir_keys', data_dir_same_redo_dir_keys)
    plugin_context.set_variable('mkdir_keys', mkdir_keys)
    plugin_context.set_variable('rm_meta', rm_meta)
    plugin_context.set_variable('stop_ob_or_obshell', stop_ob_or_obshell)
    return plugin_context.return_true()