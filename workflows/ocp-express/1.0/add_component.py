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


def add_component(plugin_context, workflow, *args, **kwargs):
    repositories = plugin_context.repositories
    repository_names = [repository.name for repository in repositories]
    workflow.add(const.STAGE_FIRST, 'parameter_pre', 'start_check_pre', 'version_check', 'general_check')

    workflow.add(const.STAGE_SECOND, 'parameter_pre')
    workflow.add_with_component_version_kwargs(const.STAGE_SECOND, const.COMP_OB_CE if const.COMP_OB_CE in repository_names else const.COMP_OB, '4.0.0.0', {'scale_out_component': const.COMP_OCP_EXPRESS}, 'connect', 'create_tenant', 'create_user')
    workflow.add(const.STAGE_SECOND, 'cursor_check', 'start', 'health_check')

    workflow.add(const.STAGE_THIRD, 'connect', 'display')
    plugin_context.return_true()
