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

"""Pure interactive: when primary RPC not enabled, choose action (restart_now/restart_later/revert), store in namespace."""

from __future__ import absolute_import, division, print_function

from tool import InteractiveUI
from _stdio import FormatText


# Values stored in namespace; core handles them
RPC_ACTION_RESTART_NOW = 'restart_now'
RPC_ACTION_REVERT = 'exit'


def rpc_action_choice(plugin_context, *args, **kwargs):
    if not plugin_context.get_variable('need_rpc_choice', spacename='seekdb'):
        return plugin_context.return_true()
    plugin_context.stdio.warn('Primary enable_rpc_service is not enabled.')
    choices = [
        'Restart now (enable in config, then stop and start primary cluster)',
        'Exit (exit without changing config)',
    ]
    while True:
        idx = InteractiveUI.single_choice('Choose action', choices, default_index=0,
            hint='↑↓ move   Enter confirm   q quit')
        if idx is None:
            plugin_context.stdio.error('Not a TTY. Run in interactive terminal.')
            return plugin_context.return_false()
        if idx < 0:
            return plugin_context.return_false()
        actions = [RPC_ACTION_RESTART_NOW, RPC_ACTION_REVERT]
        if actions[idx] == RPC_ACTION_RESTART_NOW:
            auto_restart_s = InteractiveUI.prompt(FormatText.warning('Restarting the primary instance may affect the running business. Do you want to restart it? (y/yes or n/no)'),"no")
            if InteractiveUI.parse_yes_no(auto_restart_s, default_yes=False):
                break
        else:
            return plugin_context.return_false()
    plugin_context.set_variable('rpc_action', actions[idx])
    return plugin_context.return_true()
