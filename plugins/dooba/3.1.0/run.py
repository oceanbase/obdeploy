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
