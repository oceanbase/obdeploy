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

"""Pure interactive: select install mode (standalone/primary/standby), store in namespace."""

from __future__ import absolute_import, division, print_function

from tool import InteractiveUI


def select_install_mode(plugin_context, *args, **kwargs):
    options = plugin_context.options
    standby = getattr(options, 'standby', False)
    primary = getattr(options, 'primary', False)
    if standby and primary:
        plugin_context.stdio.error('Cannot specify both --standby and --primary.')
        return plugin_context.return_false()
    if standby:
        mode = 'standby'
    elif primary:
        mode = 'primary'
    else:
        mode = 'standalone'
    plugin_context.set_variable('install_mode', mode)
    return plugin_context.return_true()
