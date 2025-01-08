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


def standby_check(plugin_context, workflow, *args, **kwargs):
    options = plugin_context.options
    workflow.add(const.STAGE_FIRST, 'get_relation_tenants')
    if not getattr(options, 'ignore_standby', False):
        workflow.add(const.STAGE_FIRST, 'get_deployment_connections')
        workflow.add_with_kwargs(const.STAGE_FIRST, {'skip_no_primary_cursor': True}, 'get_standbys')
        workflow.add(const.STAGE_FIRST, 'check_exit_standby')
    plugin_context.return_true()
