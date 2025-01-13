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


def init_pre(plugin_context, *args, **kwargs):
    data_dir_same_redo_dir_keys = ['home_path', 'data_dir', 'clog_dir', 'ilog_dir', 'slog_dir']
    data_dir_not_same_redo_dir_keys = ['home_path', 'data_dir', 'redo_dir', 'clog_dir', 'ilog_dir', 'slog_dir']
    clean_dir_keys = ['clog', 'ilog', 'slog']
    mkdir_keys = '{etc,admin,.conf,log,bin,lib}'

    dir_mapping = {
        'clog': 'redo_dir',
        'ilog': 'redo_dir',
        'slog': 'redo_dir',
    }

    def ob_clean(client=None, home_path=None, server_config=None, server=None, critical=None, EC_FAIL_TO_INIT_PATH=None):
        client.execute_command(
            "pkill -9 -u `whoami` -f '^%s/bin/observer -p %s'" % (home_path, server_config['mysql_port']))
        if client.execute_command('bash -c \'if [[ "$(ls -d {0} 2>/dev/null)" != "" && ! -O {0} ]]; then exit 0; else exit 1; fi\''.format(home_path)):
            owner = client.execute_command("ls -ld %s | awk '{print $3}'" % home_path).stdout.strip()
            err_msg = ' {} is not empty, and the owner is {}'.format(home_path, owner)
            critical(EC_FAIL_TO_INIT_PATH.format(server=server, key='home path', msg=err_msg))
        return True

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

    def same_disk_check(*args, **kwargs):
        pass

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