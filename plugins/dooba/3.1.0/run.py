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

from subprocess import Popen


def run(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    options = plugin_context.options
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    user = get_option('user', 'root')
    password = get_option('password')
    dooba_bin = get_option('dooba_bin')
    server = get_option('server')
    component = get_option('component')
    global_conf = cluster_config.get_global_conf()
    server_config = cluster_config.get_server_conf(server)

    if component in ["oceanbase", "oceanbase-ce"]:
        port = server_config.get("mysql_port")
    elif component in ["obproxy", "obproxy-ce"]:
        port = server_config.get("listen_port")
    else:
        stdio.error('Unsupported component: {}'.format(component))
        return False
    if not dooba_bin:
        stdio.error('dooba not found.Please use `--dooba-bin` to set.')
        return
    if password is None:
        if user == "root":
            if component in ["oceanbase", "oceanbase-ce"]:
                password = global_conf.get('root_password')
            elif component in ["obproxy", "obproxy-ce"]:
                password = global_conf.get('observer_root_password')
    conn_cmd = r"{dooba_bin} -h{host} -P{port} -u{user}".format(dooba_bin=dooba_bin, host=server.ip, port=port, user=user)
    if password:
        conn_cmd += " -p{}".format(password)
    stdio.verbose('execute cmd: {}'.format(conn_cmd))
    p = None
    return_code = 255
    try:
        p = Popen(conn_cmd, shell=True)
        return_code = p.wait()
    except KeyboardInterrupt:
        stdio.exception("")
        if p:
            p.kill()
    except:
        stdio.exception("")
        if p:
            p.kill()
    stdio.verbose('exit code: {}'.format(return_code))
    return return_code == 0
