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


def _get_obshell_api(obshell_client):
    if obshell_client is None:
        raise RuntimeError('OBShell client is unavailable')
    return getattr(obshell_client, 'v1', obshell_client)


def _external_address(config):
    if not config:
        return ''
    if isinstance(config, dict):
        return config.get('address') or config.get('url') or ''
    return (getattr(config, 'address', None) or
            getattr(config, 'url', None) or
            (config if isinstance(config, str) else ''))


def _is_config_not_found(error):
    return getattr(error, 'err_code', '') == 'Config.NotFound'


def _database_context(plugin_context):
    pending = [plugin_context.cluster_config]
    visited = set()
    while pending:
        cluster_config = pending.pop(0)
        config_id = id(cluster_config)
        if config_id in visited:
            continue
        visited.add(config_id)
        for component_name in getattr(cluster_config, 'depends', []):
            depend_config = cluster_config.get_depend_cluster_config(
                component_name)
            if (component_name in const.COMPS_OB_AND_SEEKDB and
                    component_name in plugin_context.namespaces):
                return (component_name,
                        plugin_context.namespaces.get(component_name))
            if depend_config is not None:
                pending.append(depend_config)
    candidates = [
        component_name for component_name in plugin_context.namespaces
        if component_name in const.COMPS_OB_AND_SEEKDB
    ]
    if len(candidates) == 1:
        component_name = candidates[0]
        return component_name, plugin_context.namespaces.get(component_name)
    return None, None


def register_to_obshell(plugin_context, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    stdio = plugin_context.stdio
    clients = plugin_context.clients
    database_component, ob_plugin_context = _database_context(plugin_context)

    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        home_path = server_config['home_path']
        client = clients[server]
        flag_file = os.path.join(home_path, '.alertmanager_started')
        if not ob_plugin_context:
            continue
        if (database_component != const.COMP_OB_SEEKDB and
                client.execute_command('ls {}'.format(flag_file))):
            continue
        try:
            obshell_client = ob_plugin_context.get_variable('obshell_client')
            obshell_api = _get_obshell_api(obshell_client)
            info = obshell_api.get_info()
            if info.version and Version(info.version.split('-')[0]) < Version('4.3.2.0'):
                continue
            if database_component == const.COMP_OB_SEEKDB:
                try:
                    current_config = obshell_api.get_alertmanager_config()
                except requests.exceptions.ConnectionError:
                    raise
                except Exception as e:
                    if not _is_config_not_found(e):
                        raise
                    stdio.verbose(
                        'Alertmanager is not registered in obshell yet')
                else:
                    if _external_address(current_config):
                        stdio.verbose(
                            'Alertmanager is already registered in obshell, skip')
                        break
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
            obshell_api.set_alertmanager_config(
                url, username or '', password or '')
            stdio.verbose(
                'register alertmanager to obshell success, url:{}'.format(url))
        except requests.exceptions.ConnectionError as e:
            stdio.warn(
                'obshell connect failed, skip register alertmanager to obshell: %s' % e)
        except Exception as e:
            stdio.warn(
                'obshell register failed, skip register alertmanager to obshell: %s' % e)
        else:
            break

    stdio.stop_loading('succeed')
    return plugin_context.return_true()
