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

"""Pure interactive: select primary cluster from list (from namespace), store selected_deploy_name."""

from __future__ import absolute_import, division, print_function

from tool import InteractiveUI


def select_primary_cluster(plugin_context, *args, **kwargs):
    mode = plugin_context.get_variable('install_mode')
    if mode != 'standby':
        return plugin_context.return_true()
    candidates = plugin_context.get_variable('primary_candidates', spacename='seekdb') or []
    if not candidates:
        plugin_context.stdio.error('No primary cluster list in namespace. Run get_primary_candidates first.')
        return plugin_context.return_false()
    idx = InteractiveUI.single_choice('Select primary cluster', candidates, default_index=0,
        hint='↑↓ move   Enter confirm   q quit')
    if idx is None:
        plugin_context.stdio.error('Not a TTY. Run in interactive terminal.')
        return plugin_context.return_false()
    if idx < 0:
        return plugin_context.return_false()
    plugin_context.set_variable('selected_primary_deploy_name', candidates[idx])
    return plugin_context.return_true()
