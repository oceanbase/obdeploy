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
    # SeekDB 1.4 owns the on-disk slog/redo layout. In particular, its first
    # startup requires the redo directory to be empty, so OBD must not create
    # the legacy redo/clog directory or data_dir/clog symlink in advance.
    directory_keys = ['home_path', 'data_dir', 'redo_dir']
    mkdir_keys = '{etc,admin,.conf,log,log_obshell,bin,lib}'

    def ob_clean(*args, **kwargs):
        pass

    def stop_ob_or_obshell(client=None, home_path=None, server=None,
                           critical=None, EC_FAIL_TO_INIT_PATH=None,
                           *args, **kwargs):
        results = []
        for bin_name in ['seekdb', 'obshell']:
            client.execute_command(
                "pkill -9 -u `whoami` -f '^%s/bin/%s'" %
                (home_path, bin_name))
            ret = client.execute_command('rm -fr %s/*' % home_path, timeout=-1)
            if not ret:
                critical(EC_FAIL_TO_INIT_PATH.format(
                    server=server, key='home path', msg=ret.stderr))
                results.append(False)
        return results

    def rm_meta(client, home_path, critical, EC_FAIL_TO_INIT_PATH, server,
                InitDirFailedErrorMessage, *args, **kwargs):
        if not client.execute_command('rm -f %s/.meta' % home_path):
            critical(EC_FAIL_TO_INIT_PATH.format(
                server=server,
                key='home path',
                msg=InitDirFailedErrorMessage.CREATE_FAILED.format(
                    path=home_path)))

    def same_disk_check(*args, **kwargs):
        # The generic resource check already reports whether data and redo use
        # the same mount. There is no separate slog path to validate in 1.4.
        pass

    plugin_context.set_variable('same_disk_check', same_disk_check)
    plugin_context.set_variable('ob_clean', ob_clean)
    plugin_context.set_variable('dir_mapping', {})
    # Create the redo directory itself, but leave it empty for the kernel.
    plugin_context.set_variable('clean_dir_keys', ['redo'])
    plugin_context.set_variable(
        'data_dir_not_same_redo_dir_keys', directory_keys)
    plugin_context.set_variable(
        'data_dir_same_redo_dir_keys', directory_keys)
    plugin_context.set_variable('default_redo_dir_subdir', 'redo')
    plugin_context.set_variable('mkdir_keys', mkdir_keys)
    plugin_context.set_variable('rm_meta', rm_meta)
    plugin_context.set_variable('stop_ob_or_obshell', stop_ob_or_obshell)
    return plugin_context.return_true()
