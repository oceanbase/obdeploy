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
    workflow.add(const.STAGE_FIRST, 'start_check', 'start', 'health_check')
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    exist_obproxy = True
    repositories = plugin_context.repositories
    repository_names = [repository.name for repository in repositories]
    workflow.add_with_component(const.STAGE_FIRST, const.COMP_OB_CE if const.COMP_OB_CE in repository_names else const.COMP_OB, 'connect', 'configserver_pre', 'register_configserver')
    for comp in const.COMPS_ODP:
        if comp in added_components:
            exist_obproxy = False
    if exist_obproxy:
        workflow.add_with_component(const.STAGE_FIRST, const.COMP_ODP_CE if const.COMP_ODP_CE in repository_names else const.COMP_ODP,  'connect', 'parameter_pre', 'register_configserver')

    workflow.add(const.STAGE_THIRD, 'connect', 'display')
    plugin_context.return_true()
