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
    workflow.add(const.STAGE_FIRST, 'start_check_pre', 'parameter_pre', 'sudo_check', 'password_check', 'tenant_check', 'java_check', 'clockdiff_check', 'tenant_check')

    workflow.add(const.STAGE_SECOND, 'parameter_pre', 'ocp_const', 'cursor_check', 'start', 'health_check', 'stop_pre')
    workflow.add_with_component(const.STAGE_SECOND, 'general', 'stop')
    workflow.add(const.STAGE_SECOND, 'start', 'health_check', 'bootstrap')

    plugin_context.return_true()
