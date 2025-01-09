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

from const import STAGE_FIRST

def commands(plugin_context, workflow, *args, **kwargs):
    context = plugin_context.get_variable('context')
    for component in context['components']:
        for repository in plugin_context.repositories:
            if repository.name == component:
                break
        for server in context['servers']:
            workflow.add_with_component_version_kwargs(0, 'commands', '0.1', {"name": plugin_context.cmds[1], "component": component, "server": server, "context": context, "repository": repository}, 'prepare_variables')
            workflow.add_with_component_version_kwargs(0, 'commands', '0.1', {'context': context, "repository": repository}, 'commands')
    plugin_context.return_true()
    