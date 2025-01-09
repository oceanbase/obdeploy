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


def scale_out(plugin_context, workflow, *args, **kwargs):
    cluster_config = plugin_context.cluster_config
    added_servers = cluster_config.added_servers

    workflow.add_with_kwargs(const.STAGE_FIRST, {'target_servers': added_servers}, 'scale_out_check')

    workflow.add_with_kwargs(const.STAGE_SECOND, {'target_servers': added_servers}, 'start_check_pre', 'parameter_pre', 'sudo_check', 'password_check', 'java_check', 'clockdiff_check', 'general_check')

    workflow.add(const.STAGE_THIRD, 'parameter_pre', 'ocp_const')
    workflow.add_with_kwargs(const.STAGE_THIRD, {'target_servers': added_servers}, 'cursor_check', 'start', 'health_check')
    workflow.add_with_component_version_kwargs(const.STAGE_THIRD, 'general', '0.1', {'target_servers': added_servers}, 'stop')
    workflow.add_with_kwargs(const.STAGE_THIRD, {'target_servers': added_servers}, 'start', 'health_check', 'bootstrap')

    plugin_context.return_true()
