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

from subprocess import call, Popen, PIPE

from ssh import LocalClient
from tool import ConfigUtil
from const import COMPS_OB


def db_connect(plugin_context, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key)
        if value is None:
            value = default
        stdio.verbose('get option: %s value %s' % (key, value))
        return value

    def local_execute_command(command, env=None, timeout=None):
        return LocalClient.execute_command(command, env, timeout, stdio)

    def get_connect_cmd():
        cmd = r"{obclient_bin} -h{host} -P{port} -u {user}@{tenant} --prompt 'OceanBase(\u@\d)>' -A".format(
            obclient_bin=obclient_bin,
            host=server.ip,
            port=port,
            user=user,
            tenant=tenant
        )
        if need_password:
            cmd += " -p"
        elif password:
            cmd += " -p{}".format(ConfigUtil.passwd_format(password))
        if database:
            cmd += " -D{}".format(database)
        return cmd

    def test_connect():
        return local_execute_command(get_connect_cmd() + " -e 'help'")

    def connect():
        conn_cmd = get_connect_cmd()
        stdio.verbose('execute cmd: {}'.format(conn_cmd))
        p = None
        return_code = 255
        try:
            p = Popen(conn_cmd, shell=True)
            return_code = p.wait()
        except:
            stdio.exception("")
            if p:
                p.kill()
        stdio.verbose('exit code: {}'.format(return_code))
        return return_code

    options = plugin_context.options
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    user = get_option('user', 'root')
    tenant = get_option('tenant', 'sys')
    database = get_option('database')
    password = get_option('password')
    obclient_bin = get_option('obclient_bin')
    server = get_option('server')
    component = get_option('component')
    global_conf = cluster_config.get_global_conf()
    server_config = cluster_config.get_server_conf(server)
    need_password = False

    # use oceanbase if root@sys as default
    if not database and user == 'root' and tenant == 'sys':
        database = 'oceanbase'

    if component in COMPS_OB:
        port = server_config.get("mysql_port")
    else:
        port = server_config.get("listen_port")
    # check the obclien avaliable
    ret = local_execute_command('%s --help' % obclient_bin)
    if not ret:
        stdio.error(
            '%s\n%s is not an executable file. Please use `--obclient-bin` to set.\nYou may not have obclient installed' % (
                ret.stderr, obclient_bin))
        return
    if not password:
        connected = test_connect()
        if not connected:
            if user == "root" and tenant == "sys":
                if component in COMPS_OB:
                    password = global_conf.get('root_password')
                elif component in ["obproxy", "obproxy-ce"]:
                    password = global_conf.get('observer_root_password')
            elif user == "root" and tenant == "proxysys":
                if component in ["obproxy", "obproxy-ce"]:
                    password = global_conf.get("obproxy_sys_password")
            elif user == "proxyro" and tenant == 'sys':
                if component in COMPS_OB:
                    password = global_conf.get("proxyro_password")
                elif component in ["obproxy", "obproxy-ce"]:
                    password = global_conf.get("observer_sys_password")
            if password:
                connected = test_connect()
        need_password = not connected
    try:
        code = connect()
    except KeyboardInterrupt:
        stdio.exception("")
        return False
    return code == 0
