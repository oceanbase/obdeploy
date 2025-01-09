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


def add_component_pre(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_components = cluster_config.get_deploy_added_components()
    if const.COMP_OB_CONFIGSERVER in added_components:
        cluster_config.add_depend_component(const.COMP_OB_CONFIGSERVER)
    if cluster_config.name not in added_components:
        return plugin_context.return_true()
    workflow.add_with_kwargs(const.STAGE_FIRST, {'auto_depend': True}, 'generate_config')
    repositories = plugin_context.repositories
    repository_names = [repository.name for repository in repositories]
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'oceanbase-ce' if 'oceanbase-ce' in repository_names else 'oceanbase',
                                               '4.0.0.0', {'scale_out_component': plugin_context.cluster_config.name}, 'connect')
    workflow.add(const.STAGE_FIRST, 'init', 'start_check_pre', 'status_check', 'password_check', 'status_check', 'work_dir_check', 'proxy_id_check', 'port_check')
    workflow.add(const.STAGE_THIRD, 'parameter_pre')
    plugin_context.return_true()
