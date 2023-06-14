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
from subprocess import call, Popen, PIPE
import _errno as err
import os


def gather_perf(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def local_execute_command(command, env=None, timeout=None):
        command = r"cd {install_dir} && sh ".format(install_dir=obdiag_install_dir) + command
        return LocalClient.execute_command(command, env, timeout, stdio)

    def get_obdiag_cmd():
        base_commond=r"cd {install_dir} && sh obdiag gather perf".format(install_dir=obdiag_install_dir)
        cmd = r"{base} --scope {scope_option} ".format(
            base = base_commond,
            scope_option = scope_option
        )
        if store_dir_option:
            cmd = cmd + r" --store_dir {store_dir_option}".format(store_dir_option=store_dir_option)
        if ob_install_dir_option:
            cmd = cmd + r" --ob_install_dir {ob_install_dir_option}".format(ob_install_dir_option=ob_install_dir_option)
        return cmd

    def run():
        obdiag_cmd = get_obdiag_cmd()
        stdio.verbose('execute cmd: {}'.format(obdiag_cmd))
        p = None
        return_code = 255
        try:
            p = Popen(obdiag_cmd, shell=True)
            return_code = p.wait()
        except:
            stdio.exception("")
            if p:
                p.kill()
        stdio.verbose('exit code: {}'.format(return_code))
        return return_code == 0

    options = plugin_context.options
    obdiag_bin = "obdiag"
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    global_conf = cluster_config.get_global_conf()
    ob_install_dir_option=global_conf.get('home_path')
    scope_option = get_option('scope')
    store_dir_option = os.path.abspath(get_option('store_dir'))
    obdiag_install_dir = get_option('obdiag_dir')

    ret = local_execute_command('%s --help' % obdiag_bin)
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()
    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag gather perf failded")
        return plugin_context.return_false()