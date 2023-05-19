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
import datetime
import os
from tool import TimeUtils
from subprocess import call, Popen, PIPE
import _errno as err


def gather_clog(plugin_context, *args, **kwargs):
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
        base_commond = r"cd {install_dir} && sh obdiag gather clog".format(install_dir=obdiag_install_dir)
        cmd = r"{base} --clog_dir {data_dir} --from {from_option} --to {to_option} --encrypt {encrypt_option}".format(
            base = base_commond,
            data_dir = data_dir,
            from_option = from_option,
            to_option = to_option,
            encrypt_option = encrypt_option
        )
        if ob_install_dir_option:
            cmd = cmd + r" --ob_install_dir {ob_install_dir_option}".format(ob_install_dir_option=ob_install_dir_option)
        if store_dir_option:
            cmd = cmd + r" --store_dir {store_dir_option}".format(store_dir_option=store_dir_option)
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
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    global_conf = cluster_config.get_global_conf()
    from_option = get_option('from')
    to_option = get_option('to')
    since_option = get_option('since')
    encrypt_option = get_option('encrypt')
    store_dir_option = get_option('store_dir')
    ob_install_dir_option = global_conf.get('home_path')
    data_dir = ob_install_dir_option + "/store"
    obdiag_install_dir = get_option('obdiag_dir')

    if len(cluster_config.servers) > 0:
        server_config = cluster_config.get_server_conf(cluster_config.servers[0])
        if not server_config.get('data_dir'):
            server_config['data_dir'] = '%s/store' % ob_install_dir_option
        if not server_config.get('redo_dir'):
            server_config['redo_dir'] = server_config['data_dir']
        if not server_config.get('clog_dir'):
            server_config['clog_dir'] = '%s/clog' % server_config['redo_dir']
        data_dir = server_config['clog_dir']

    try:
        if (not from_option) and (not to_option) and since_option:
            now_time = datetime.datetime.now()
            to_option = (now_time + datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
            from_option = (now_time - datetime.timedelta(seconds=TimeUtils.parse_time_sec(since_option))).strftime('%Y-%m-%d %H:%M:%S')
    except:
        stdio.error(err.EC_OBDIAG_OPTIONS_FORMAT_ERROR.format(option="since", value=since_option))
        return plugin_context.return_false()


    ret = local_execute_command('%s --help' % obdiag_bin)
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()
    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag gather clog failded")
        return plugin_context.return_false()