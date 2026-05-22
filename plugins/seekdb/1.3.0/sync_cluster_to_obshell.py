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

import re

from obshell import ClientSet, ClientV1
from obshell.auth import PasswordAuth
from obshell.request import ProtocolOptions


def _get_cluster_endpoint(cluster_config):
    server = cluster_config.servers[0]
    server_config = cluster_config.get_server_conf_with_default(server)
    global_conf = cluster_config.get_global_conf()
    root_password = server_config.get('root_password')
    if root_password is None:
        root_password = global_conf.get('root_password', '')

    return {
        'ip': server.ip,
        'rpc_port': int(server_config.get('rpc_port', 2882)),
        'obshell_port': int(server_config.get('obshell_port', 2886)),
        'root_password': root_password or '',
    }


def _extract_token(token_resp):
    if not token_resp:
        return None
    if hasattr(token_resp, 'token'):
        return token_resp.token
    if isinstance(token_resp, dict):
        token = token_resp.get('token')
        if token:
            return token
        data = token_resp.get('data') or {}
        if isinstance(data, dict):
            return data.get('token')
    return None


def _new_client_and_token(cluster_meta):
    client = ClientSet(
        cluster_meta['ip'],
        cluster_meta['obshell_port'],
        PasswordAuth(cluster_meta['root_password']),
    )
    try:
        token_resp = client.v1.get_seekdb_standby_token()
        return client.v1, token_resp
    except Exception as e:
        match = re.search(r'status code: (\d+)', str(e))
        if match and match.group(1) == '400':
            client = ClientV1(
                cluster_meta['ip'],
                cluster_meta['obshell_port'],
                PasswordAuth(cluster_meta['root_password']),
                protocol_options=ProtocolOptions.https_insecure(),
            )
            token_resp = client.get_seekdb_standby_token()
            return client, token_resp
        raise RuntimeError(
            'Failed to get seekdb standby token from %s:%s'
            % (cluster_meta['ip'], cluster_meta['obshell_port'])
        )


def sync_cluster_to_obshell(plugin_context, *args, **kwargs):
    stdio = plugin_context.stdio
    mode = plugin_context.get_variable('install_mode', spacename='interactive')
    if mode != 'standby':
        stdio.verbose('Current install mode is not standby, skip obshell standby pair sync.')
        return plugin_context.return_true()

    primary_deploy_name = plugin_context.get_variable('primary_deploy_name')
    if not primary_deploy_name:
        stdio.verbose('No primary_deploy_name found, skip obshell standby pair sync.')
        return plugin_context.return_true()

    deploy_manager = kwargs.get('deploy_manager')
    if not deploy_manager:
        stdio.error('deploy_manager missing, can not sync standby pair to obshell.')
        return plugin_context.return_false()

    primary_deploy = deploy_manager.get_deploy_config(primary_deploy_name)
    if not primary_deploy:
        stdio.error('Primary deploy "%s" not found.' % primary_deploy_name)
        return plugin_context.return_false()

    primary_cluster_config = primary_deploy.deploy_config.components.get('seekdb')
    standby_cluster_config = plugin_context.cluster_config
    if not primary_cluster_config or not standby_cluster_config:
        stdio.error('Failed to load seekdb cluster config from primary or standby deploy.')
        return plugin_context.return_false()

    primary_meta = _get_cluster_endpoint(primary_cluster_config)
    standby_meta = _get_cluster_endpoint(standby_cluster_config)

    stdio.start_loading('Sync standby relation to obshell')
    try:
        primary_client, primary_token_resp = _new_client_and_token(primary_meta)
        standby_client, standby_token_resp = _new_client_and_token(standby_meta)

        primary_token = _extract_token(primary_token_resp)
        standby_token = _extract_token(standby_token_resp)

        if not primary_token:
            raise Exception('Primary token is empty.')
        if not standby_token:
            raise Exception('Standby token is empty.')

        primary_client.set_seekdb_standby_pair(
            peer_host=standby_meta['ip'],
            peer_obshell_port=standby_meta['obshell_port'],
            peer_rpc_port=standby_meta['rpc_port'],
            direction='DOWNSTREAM',
            token=standby_token,
        )
        standby_client.set_seekdb_standby_pair(
            peer_host=primary_meta['ip'],
            peer_obshell_port=primary_meta['obshell_port'],
            peer_rpc_port=primary_meta['rpc_port'],
            direction='UPSTREAM',
            token=primary_token,
        )

        primary_status = primary_client.get_seekdb_standby_status()
        standby_status = standby_client.get_seekdb_standby_status()
        stdio.verbose('Primary obshell standby status: %s' % primary_status)
        stdio.verbose('Standby obshell standby status: %s' % standby_status)
        stdio.stop_loading('succeed')
    except Exception as e:
        stdio.stop_loading('fail')
        stdio.warn('Sync standby relation to obshell failed: %s' % e)

    return plugin_context.return_true()
