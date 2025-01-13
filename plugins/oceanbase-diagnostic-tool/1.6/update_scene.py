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
from ssh import LocalClient
import _errno as err
import os


def update_scene(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def local_execute_command(command, env=None, timeout=None):
        command = r"{install_dir}/obdiag".format(install_dir=obdiag_install_dir)
        return LocalClient.execute_command(command, env, timeout, stdio)

    def get_obdiag_cmd():
        base_commond=r"{install_dir}/obdiag update ".format(install_dir=obdiag_install_dir)
        cmd = r"{base}".format(
            base=base_commond,
        )
        if file_option:
            cmd = cmd + r" --file {option}".format(option=file_option)
        if force_option:
            cmd = cmd + r" --force {option}".format(option=force_option)
        return cmd

    def run():
        obdiag_cmd = get_obdiag_cmd()
        stdio.verbose('execute cmd: {}'.format(obdiag_cmd))
        return LocalClient.run_command(obdiag_cmd, env=None, stdio=stdio)

    options = plugin_context.options
    obdiag_bin = "obdiag"
    stdio = plugin_context.stdio
    obdiag_install_dir = get_option('obdiag_dir')
    file_option = get_option('file')
    if file_option:
        file_option = os.path.abspath(get_option('file'))
    force_option = get_option('force')

    ret = local_execute_command('%s --help' % obdiag_bin)
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()
    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag update failed")
        return plugin_context.return_false()