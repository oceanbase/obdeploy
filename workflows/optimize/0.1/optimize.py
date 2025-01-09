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

import const

def optimize(plugin_context, workflow, repository, *args, **kwargs):
    optimize_config = kwargs.get('optimize_config')
    connect_namespace = kwargs.get('connect_namespaces')
    get_db_and_cursor = kwargs.get("get_db_and_cursor")

    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'optimize', "0.1", {'optimize_config': optimize_config, 'repository': repository}, 'check_options')

    for namespace in connect_namespace:
        db, cursor = get_db_and_cursor(namespace)
        if not db or not cursor:
            workflow.add_with_component_version_kwargs(const.STAGE_SECOND, repository.name, repository.version, {"spacename": namespace.spacename}, 'connect')

    workflow.add_with_component_version_kwargs(const.STAGE_THIRD, 'optimize', "0.1", {'repository': repository, **kwargs}, 'optimize')

    return plugin_context.return_true()

