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

"""OBShell bootstrap after start. Reference: OceanBase 4.2.1.4 obshell_bootstrap."""

from __future__ import absolute_import, division, print_function

import time
import re

import requests.exceptions
from obshell import ClientSet, ClientV1
from obshell.auth import PasswordAuth
from obshell.model.info import Agentidentity
from obshell.request import ProtocolOptions


def _new_obshell_client(server, server_config):
    root_password = server_config.get('root_password', '')
    obshell_port = server_config.get('obshell_port', 2886)
    return ClientSet(server.ip, obshell_port, PasswordAuth(root_password))


def _get_obshell_info(server, server_config, client):
    """Return a protocol-compatible client and its agent information."""
    try:
        obshell_api = getattr(client, 'v1', client)
        return client, obshell_api.get_info()
    except requests.exceptions.ConnectionError:
        raise
    except Exception as e:
        match = re.search(r'status code: (\d+)', str(e))
        if (not hasattr(client, 'v1') or not match or
                match.group(1) != '400'):
            raise
        client = ClientV1(
            server.ip,
            server_config.get('obshell_port', 2886),
            PasswordAuth(server_config.get('root_password', '')),
            protocol_options=ProtocolOptions.https_insecure(),
        )
        return client, client.get_info()


def _publish_existing_obshell_client(plugin_context):
    """Publish a client without changing the existing cluster identity.

    A normal start skips takeover/bootstrap after SeekDB data already exists,
    but later component plugins still need an authenticated OBShell client.
    Client discovery is deliberately best-effort so this path preserves the
    historical behavior where a running SeekDB is not failed by this step.
    """
    cluster_config = plugin_context.cluster_config
    fallback_client = None
    for server in cluster_config.servers:
        server_config = cluster_config.get_server_conf(server)
        client = _new_obshell_client(server, server_config)
        if fallback_client is None:
            fallback_client = client
        try:
            client, _ = _get_obshell_info(server, server_config, client)
        except Exception as e:
            plugin_context.stdio.verbose(
                'Failed to initialize obshell client %s:%s: %s',
                server.ip, server_config.get('obshell_port', 2886), e)
            continue
        plugin_context.set_variable('obshell_client', client)
        return
    if fallback_client is not None:
        # Keep registration best-effort. The consumer will surface the actual
        # connection error and can retry after OBShell becomes ready.
        plugin_context.set_variable('obshell_client', fallback_client)


def obshell_bootstrap(plugin_context, need_bootstrap=None, *args, **kwargs):
    scale_out = plugin_context.get_variable('scale_out')
    stdio = plugin_context.stdio
    cluster_config = plugin_context.cluster_config
    if not need_bootstrap and not scale_out:
        _publish_existing_obshell_client(plugin_context)
        return plugin_context.return_true()
    if plugin_context.get_variable('seekdb_is_standby', default=False):
        _publish_existing_obshell_client(plugin_context)
        stdio.print('Standby cluster: skip OBShell bootstrap.')
        return plugin_context.return_true()
    stdio.start_loading('obshell bootstrap')
    time.sleep(3)
    try:
        count = 200
        obshell_clients = {}
        while count:
            take_over_count = 0
            for server in cluster_config.servers:
                if server not in obshell_clients:
                    server_config = cluster_config.get_server_conf(server)
                    client = _new_obshell_client(server, server_config)
                    obshell_clients[server] = client
                else:
                    server_config = cluster_config.get_server_conf(server)
                client = obshell_clients[server]
                try:
                    client, info = _get_obshell_info(
                        server, server_config, client)
                    obshell_clients[server] = client
                except requests.exceptions.ConnectionError:
                    continue
                except Exception:
                    obshell_port = server_config.get('obshell_port', 2886)
                    stdio.error('Failed to connect obshell %s:%s' %
                                (server.ip, obshell_port))
                    return plugin_context.return_false()

                obshell_api = getattr(client, 'v1', client)
                if info.identity == Agentidentity.TAKE_OVER_MASTER.value:
                    dag = obshell_api.get_agent_last_maintenance_dag()
                    obshell_api.wait_dag_succeed(dag.generic_id)
                    take_over_count = len(cluster_config.servers)
                    break
                elif info.identity == Agentidentity.CLUSTER_AGENT.value:
                    take_over_count += 1
            if take_over_count == len(cluster_config.servers):
                break
            time.sleep(3)
            count -= 1
        if count == 0:
            stdio.stop_loading('fail')
            stdio.error('obshell bootstrap failed: get obshell take over result timeout!')
            return plugin_context.return_false()
    except Exception as e:
        stdio.exception('')
        stdio.stop_loading('fail')
        stdio.error('obshell bootstrap failed: %s' % e)
        return plugin_context.return_false()

    plugin_context.set_variable('obshell_client', client)
    stdio.stop_loading('succeed')

    return plugin_context.return_true()
