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

from ssh import LocalClient


def recover(plugin_context, optimize_config, optimize_envs=None, *args, **kwargs):
    stdio = plugin_context.stdio
    client = LocalClient
    if optimize_envs is None:
        optimize_envs = {}
    stdio.start_loading("Recover")
    optimize_config.set_envs(optimize_envs)
    optimize_envs['optimize_entrances_done'] = optimize_envs.get('optimize_entrances_done', {})
    restart_components = []
    for component, entrances in optimize_envs['optimize_entrances_done'].items():
        if component in ['oceanbase', 'oceanbase-ce', 'oceanbase-standalone', 'obproxy', 'obproxy-ce']:
            cursor = plugin_context.get_return('connect', spacename=component).get_return('cursor')
        else:
            raise Exception('Invalid component {}'.format(component))
        for entrance in entrances[::-1]:
            entrance.recover(cursor=cursor, client=client, stdio=stdio)
            if entrance.need_restart:
                restart_components.append(component)
    stdio.stop_loading("succeed")
    return plugin_context.return_true(restart_components=restart_components)
