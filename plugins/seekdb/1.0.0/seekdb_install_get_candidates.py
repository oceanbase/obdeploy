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

"""SeekDB install: get running SeekDB deploy list, store primary_candidates via set_variable. Exclude clusters with loopback IP (127.x.x.x)."""

from __future__ import absolute_import, division, print_function

from _deploy import DeployStatus


def _is_loopback_ip(ip):
    """True if ip is 127.x.x.x or localhost. Standby primary list should not show such clusters."""
    if not ip:
        return False
    ip = str(ip).strip()
    if ip in ('127.0.0.1', 'localhost'):
        return True
    if ip.startswith('127.'):
        return True
    return False


def seekdb_install_get_candidates(plugin_context, deploy_manager=None, *args, **kwargs):
    if not deploy_manager:
        plugin_context.stdio.error('deploy_manager is required.')
        return plugin_context.return_false()
    mode = plugin_context.get_variable('install_mode', spacename='interactive')
    if mode != 'standby':
        return plugin_context.return_true()
    all_deploys = deploy_manager.get_deploy_configs()
    seekdb_deploys = [
        d for d in all_deploys
        if (d.deploy_info.components or {}).get('seekdb') is not None
        and d.deploy_info.status == DeployStatus.STATUS_RUNNING
    ]
    # Exclude clusters whose first server IP is loopback (127.x.x.x) from primary list
    def _first_server_ip(deploy):
        comp = deploy.deploy_config.components.get('seekdb') if getattr(deploy, 'deploy_config', None) else None
        if not comp or not getattr(comp, 'servers', None) or len(comp.servers) < 1:
            return None
        return getattr(comp.servers[0], 'ip', None)
    seekdb_deploys = [d for d in seekdb_deploys if not _is_loopback_ip(_first_server_ip(d))]
    if not seekdb_deploys:
        plugin_context.stdio.error('No running SeekDB cluster found (or all have loopback IP 127.x.x.x). Deploy and start a SeekDB cluster with a non-loopback IP first.')
        return plugin_context.return_false()
    plugin_context.set_variable('primary_candidates', [d.name for d in seekdb_deploys])
    return plugin_context.return_true()
