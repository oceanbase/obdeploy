# coding: utf-8
# OceanBase Deploy.
# Copyright (C) 2021 OceanBase
#
# This file is part of OceanBase Deploy.
#
# OceanBase Deploy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OceanBase Deploy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OceanBase Deploy.  If not, see <https://www.gnu.org/licenses/>.

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
        if component in ['oceanbase', 'oceanbase-ce', 'obproxy', 'obproxy-ce']:
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
