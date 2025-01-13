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
import os
import _errno as err


def analyze_flt_trace(plugin_context, *args, **kwargs):
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
        base_commond=r"{install_dir}/obdiag analyze flt_trace --flt_trace_id {trace_id}".format(install_dir=obdiag_install_dir, trace_id=flt_trace_id)
        cmd = base_commond
        if files_option_path:
            cmd = r"{base} --files {files_option_path}".format(
            base = base_commond,
            files_option_path = files_option_path,
            )
        if store_dir_option:
            cmd = cmd + r" --store_dir {store_dir_option}".format(store_dir_option=store_dir_option)
        if top_option:
            cmd = cmd + r" --top '{top_option}'".format(top_option=top_option)
        if recursion_option:
            cmd = cmd + r" --recursion '{recursion_option}'".format(recursion_option=recursion_option)
        if output_option:
            cmd = cmd + r" --output '{output_option}'".format(output_option=output_option)
        return cmd

    def run():
        obdiag_cmd = get_obdiag_cmd()
        stdio.verbose('execute cmd: {}'.format(obdiag_cmd))
        return LocalClient.run_command(obdiag_cmd, env=None, stdio=stdio)

    options = plugin_context.options
    obdiag_bin = "obdiag"
    files_option_path = None
    stdio = plugin_context.stdio
    top_option = get_option('top')
    recursion_option = get_option('recursion')
    output_option = get_option('output')
    files_option = get_option('files')
    if files_option:
        files_option_path = os.path.abspath(get_option('files'))
    store_dir_option = os.path.abspath(get_option('store_dir'))
    obdiag_install_dir = get_option('obdiag_dir')
    flt_trace_id = get_option('flt_trace_id')
    ret = local_execute_command('%s --help' % obdiag_bin)
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()
    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag analyze log failed")
        return plugin_context.return_false()