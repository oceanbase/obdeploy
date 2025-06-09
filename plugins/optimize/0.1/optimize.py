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


def optimize(plugin_context, optimize_config, stage, optimize_envs=None, *args, **kwargs):
    def get_option(key, default=''):
        value = getattr(options, key, default)
        if value is None:
            value = default
        return value

    stdio = plugin_context.stdio
    options = plugin_context.options
    stdio.start_loading('Optimize for stage {}'.format(stage))
    stdio.verbose('optimize_envs: {}'.format(optimize_envs))
    optimization = int(get_option('optimization', 0))
    if optimization <= 0:
        stdio.verbose('Do not need to optimize')
        return plugin_context.return_true()
    components = plugin_context.components
    client = LocalClient
    if optimize_envs is None:
        optimize_envs = {}
    optimize_config.set_envs(optimize_envs)
    restart_components = []
    optimize_envs['optimize_entrances_done'] = optimize_envs.get('optimize_entrances_done', {})
    for component in components:
        if component in ['oceanbase', 'oceanbase-ce', 'oceanbase-standalone', 'obproxy', 'obproxy-ce']:
            connect = plugin_context.get_return('connect', spacename=component)
            if not connect:
                continue
            cursor = connect.get_return('cursor')
        else:
            continue
        if not cursor:
            continue
        optimize_envs['optimize_entrances_done'][component] = optimize_envs['optimize_entrances_done'].get(component, [])
        optimize_entrances = optimize_config.get_optimize_entrances(component, stage)
        for entrance in optimize_entrances:
            opt_kwargs = dict(cursor=cursor, client=client, stdio=stdio)
            if optimization == 1:
                opt_kwargs.update(disable_restart=True)
            if entrance.optimize(**opt_kwargs):
                stdio.verbose('optimize {} success'.format(entrance.__class__.__name__))
                optimize_envs['optimize_entrances_done'][component].append(entrance)
                if entrance.need_restart and component not in restart_components:
                    stdio.verbose('{} need restart.'.format(component))
                    restart_components.append(component)
            else:
                stdio.verbose('optimize {} failed'.format(entrance))
                stdio.stop_loading('fail')
                return plugin_context.return_false()
    stdio.stop_loading("succeed")
    return plugin_context.return_true(restart_components=restart_components)
