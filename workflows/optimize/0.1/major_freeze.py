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

def major_freeze(plugin_context, workflow, repository, *args, **kwargs):
    connect_namespaces = kwargs.get("connect_namespaces")
    ob_repository = kwargs.get("ob_repository")
    restart_components = kwargs.get("restart_components")
    optimize_envs = kwargs.get("optimize_envs")

    stdio = plugin_context.stdio
    if not connect_namespaces:
        pass
    for namespace in connect_namespaces:
        workflow.add_with_component_version_kwargs(const.STAGE_FIRST, repository.name, repository.version, {"spacename": namespace.spacename}, 'connect')
        if namespace.spacename == ob_repository.name and ob_repository.name in restart_components:
            stdio.verbose('{}: major freeze for component ready'.format(ob_repository.name))
            workflow.add_with_component_version_kwargs(const.STAGE_SECOND, ob_repository.name, ob_repository.version, {"tenant": optimize_envs.get('tenant')}, 'major_freeze')
    return plugin_context.return_true()
            
    

