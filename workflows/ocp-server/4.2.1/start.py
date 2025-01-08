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


def start(plugin_context, workflow, *args, **kwargs):
    repositories = plugin_context.repositories
    clients = kwargs.get('component_kwargs', {}).get('new_clients', {})
    repository_name = [repository.name for repository in repositories]

    workflow.add(const.STAGE_FIRST, 'parameter_pre', 'ocp_const')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {'new_clients': clients}, 'chown_dir')
    if not plugin_context.cluster_config.depends:
        workflow.add_with_kwargs(const.STAGE_FIRST, {'need_connect': False}, 'cursor_check')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, const.COMP_OB_CE if const.COMP_OB_CE in repository_name else const.COMP_OB, '4.0.0.0', {'scale_out_component': const.COMP_OCP_SERVER_CE}, 'connect', 'create_tenant', 'create_user', 'import_time_zone')
    workflow.add(const.STAGE_FIRST, 'start', 'health_check')
    workflow.add(const.STAGE_FIRST, 'stop_pre')
    workflow.add_with_component(const.STAGE_FIRST, 'general', 'stop')
    workflow.add(const.STAGE_FIRST, 'start', 'health_check', 'bootstrap', 'connect', 'upload_packages')
    plugin_context.return_true()
