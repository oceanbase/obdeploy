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

import os

import requests

import const
from _rpm import Version
from tool import NetUtil


def register_to_obshell(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        client = clients[server]
        ob_plugin_context = None
        for namespace in plugin_context.namespaces:
            if namespace in const.COMPS_OB:
                ob_plugin_context = plugin_context.namespaces.get(namespace)
                break
        flag_file = os.path.join(home_path, '.alertmanager_started')
        if not (ob_plugin_context and not client.execute_command('ls {}'.format(flag_file))):
            continue
        try:
            obshell_client = ob_plugin_context.get_variable('obshell_client')
            info = obshell_client.v1.get_info()
            if info.version and Version(info.version.split('-')[0]) < Version('4.3.2.0'):
                continue
            config = cluster_config.get_server_conf(server)
            username = None
            password = None
            if config.get('basic_auth_users'):
                username, password = list(config['basic_auth_users'].items())[0]
            ip = server.ip
            if ip == '127.0.0.1':
                ip = NetUtil.get_host_ip()
            ssl = False
            if config.get('web_config', {}).get('tls_server_config'):
                if config['web_config']['tls_server_config'] and (config['web_config']['tls_server_config'].get('cert_file') or config['web_config']['tls_server_config'].get('cert')):
                    ssl = True
            protocol = 'https' if ssl else 'http'
            url = '%s://%s:%s' % (protocol, ip, server_config['port'])
            obshell_client.v1.set_alertmanager_config(url, username, password if password else "")
            stdio.verbose('register alertmanager to obshell success, url:{}'.format(obshell_client.v1.get_alertmanager_config()))
        except requests.exceptions.ConnectionError:
            stdio.warn('obshell connect failed, skip register alertmanager to obshell')
        except:
            stdio.warn('obshell register failed, skip register alertmanager to obshell')
        break

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
