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

import os
from ssh import LocalClient
from tool import TimeUtils
import _errno as err


def gather_all(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def local_execute_command(command, env=None, timeout=None):
        command = r"cd {install_dir} && ./".format(install_dir=obdiag_install_dir) + command
        return LocalClient.execute_command(command, env, timeout, stdio)

    def get_obdiag_cmd():
        base_commond=r"cd {install_dir} && ./obdiag gather all".format(install_dir=obdiag_install_dir)
        cmd = r"{base} --from {from_option} --to {to_option} --scope {scope_option} --encrypt {encrypt_option}".format(
            base=base_commond,
            from_option=from_option,
            to_option=to_option,
            scope_option=scope_option,
            encrypt_option=encrypt_option,
        )
        if grep_option:
            cmd = cmd + r" --grep {grep_option}".format(grep_option=grep_option)
        if store_dir_option:
            cmd = cmd + r" --store_dir {store_dir_option}".format(store_dir_option=store_dir_option)
        return cmd

    def run():
        obdiag_cmd = get_obdiag_cmd()
        stdio.verbose('execute cmd: {}'.format(obdiag_cmd))
        return LocalClient.run_command(obdiag_cmd, env=None, stdio=stdio)

    options = plugin_context.options
    obdiag_bin = "obdiag"
    stdio = plugin_context.stdio
    from_option = get_option('from')
    to_option = get_option('to')
    scope_option = get_option('scope')
    since_option = get_option('since')
    grep_option = get_option('grep')
    encrypt_option = get_option('encrypt')
    store_dir_option = os.path.abspath(get_option('store_dir'))
    obdiag_install_dir = get_option('obdiag_dir')
    from_option, to_option, ok = TimeUtils.parse_time_from_to(from_time=from_option, to_time=to_option, stdio=stdio)
    if not ok:
        from_option, to_option = TimeUtils.parse_time_since(since=since_option)

    ret = local_execute_command('%s --help' % obdiag_bin)
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()
    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag gather all failed")
        return plugin_context.return_false()