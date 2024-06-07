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