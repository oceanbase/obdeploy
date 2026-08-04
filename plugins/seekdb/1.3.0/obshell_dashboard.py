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

from _rpm import Version
from tool import NetUtil
from obshell import ClientV1


def compare(obshell_version, version, op):
    if op == '>':
        return obshell_version > version
    elif op == '<':
        return obshell_version > version
    elif op == '>=':
        return obshell_version >= version
    elif op == '<=':
        return obshell_version <= version
    elif op == '==':
        return obshell_version == version
    elif op == '!=':
        return obshell_version != version
    else:
        return False


def passwd_format(passwd):
    return "'{}'".format(passwd.replace("'", "'\"'\"'"))


def obshell_dashboard(plugin_context, config_encrypted, display_encrypt_password='******', obshell_clients=None, skip_when_status_check_failed=False, *args, **kwargs):
    if skip_when_status_check_failed and plugin_context.get_variable('status_check_pass') is False:
        return plugin_context.return_true()

    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    if plugin_context.get_variable('seekdb_is_standby', default=False):
        return plugin_context.return_true()
    if not config_encrypted:
        display_encrypt_password = None
    stdio.start_loading("display obshell dashboard")
    ip = cluster_config.servers[0].ip
    client = obshell_clients[ip]
    try:
        if type(client) is ClientV1:
            obshell_version_ret = client.get_info()
        else:
            obshell_version_ret = client.v1.get_info()
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.error(e)
        return plugin_context.return_false()
    obshell_version = obshell_version_ret.version.split('-')[0]
    dashboard_info = ''
    if compare(obshell_version, Version('4.3.0.0'), '>='):
        server_config = cluster_config.get_server_conf(cluster_config.servers[0])
        obshell_port = server_config.get("obshell_port")
        if ip == '127.0.0.1':
            ip = NetUtil.get_host_ip()
        dashboard_info = "http://{ip}:{port}".format(ip=ip, port=str(obshell_port))
        dashboard_info_list = [{
            "url": dashboard_info,
            "user": "root",
            "password": passwd_format(cluster_config.get_global_conf().get('root_password', '')
                                      if not display_encrypt_password else display_encrypt_password)
        }]
        stdio.print_list(
            dashboard_info_list,
            ['url', 'user', 'password', 'status'],
            lambda x: [x['url'], x['user'], x['password'], 'active'],
            title="obshell Dashboard"
        )

    stdio.stop_loading('succeed')
    return plugin_context.return_true(obshell_dashboard=dashboard_info)
