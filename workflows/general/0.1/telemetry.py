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

from const import STAGE_FIRST, STAGE_SECOND


def telemetry(plugin_context, workflow, *args, **kwargs):
    workflow.add_with_component_version_kwargs(STAGE_FIRST, 'general', '0.1', {"spacename": 'telemetry'}, 'telemetry_info_collect')
    workflow.add_with_component_version_kwargs(STAGE_SECOND, 'general', '0.1', {"spacename": 'telemetry'}, 'telemetry_post')
    plugin_context.return_true()