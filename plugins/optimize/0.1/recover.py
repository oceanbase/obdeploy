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
        if component in ['oceanbase', 'oceanbase-ce', 'obproxy', 'obproxy-ce']:
            cursor = plugin_context.get_return('connect', spacename=component).get_return('cursor')
        else:
            raise Exception('Invalid component {}'.format(component))
        for entrance in entrances[::-1]:
            entrance.recover(cursor=cursor, client=client, stdio=stdio)
            if entrance.need_restart:
                restart_components.append(component)
    stdio.stop_loading("succeed")
    return plugin_context.return_true(restart_components=restart_components)
