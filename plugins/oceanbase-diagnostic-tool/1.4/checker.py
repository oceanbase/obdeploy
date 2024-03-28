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
import _errno as err
import sys
import os
from tool import FileUtil, YamlLoader

if sys.version_info.major == 2:
    import MySQLdb as mysql
else:
    import pymysql as mysql

def checker(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    options = plugin_context.options
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
        base_commond = r"{install_dir}/obdiag check".format(install_dir=obdiag_install_dir)
        cmd=base_commond
        options_dict = vars(options)
        # check options
        for option, value in options_dict.items():
            if value is not None:
                if option is "obdiag_dir":
                    continue
                cmd += ' --{}={}'.format(option, value)
        return cmd

    def run():
        obdiag_cmd = get_obdiag_cmd()
        stdio.verbose('execute cmd: {}'.format(obdiag_cmd))
        return LocalClient.run_command(obdiag_cmd, env=None, stdio=stdio)

    obdiag_bin = "obdiag"
    cases = get_option('cases')
    obdiag_install_dir = get_option('obdiag_dir')
    # get obdiag_conf
    obdiag_conf_yaml_path = os.path.join(os.path.expanduser('~'), ".obdiag/config.yml")
    with FileUtil.open(obdiag_conf_yaml_path) as f:
        obdiag_info = YamlLoader(stdio=stdio).load(f)
    obdiag_obcluster_info = obdiag_info['obcluster']
    db_host = obdiag_obcluster_info["db_host"]
    db_port = obdiag_obcluster_info["db_port"]
    db_user = obdiag_obcluster_info["tenant_sys"]["user"]
    db_password = obdiag_obcluster_info["tenant_sys"]["password"]
    
    ret = local_execute_command('%s --help' % obdiag_bin)
    if not ret:
        stdio.error(err.EC_OBDIAG_NOT_FOUND.format())
        return plugin_context.return_false()

    stdio.start_loading('Check database connectivity')
    try:
        mysql.connect(host=db_host, user=db_user, port=int(db_port), password=str(db_password), cursorclass=mysql.cursors.DictCursor)
    except Exception:
        stdio.stop_loading('fail')
        stdio.error('cluster :{0} . Invalid cluster information. Please check the conf in OBD'.format(obdiag_obcluster_info))
        return plugin_context.return_false()
    stdio.stop_loading('succeed')
    
    try:
        if run():
            plugin_context.return_true()
    except KeyboardInterrupt:
        stdio.exception("obdiag check failed")
        return plugin_context.return_false()
