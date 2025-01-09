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
    pre_exist_server = list(filter(lambda x: x not in added_servers, cluster_config.servers))

    workflow.add_with_kwargs(const.STAGE_FIRST, {'target_servers': added_servers}, 'start_check_pre', 'status_check', 'parameter_check', 'system_limits_check', 'resource_check', 'environment_check')

    workflow.add_with_kwargs(const.STAGE_SECOND, {'target_servers': added_servers}, 'configserver_pre', 'start_pre', 'start', 'health_check', 'connect', 'bootstrap')

    workflow.add_with_kwargs(const.STAGE_THIRD, {'target_servers': pre_exist_server}, 'connect', 'scale_out')
    plugin_context.return_true()
