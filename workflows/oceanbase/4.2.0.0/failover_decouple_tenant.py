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


def failover_decouple_tenant(plugin_context, workflow, *args, **kwargs):
    options = plugin_context.options
    if not getattr(options, 'skip_cluster_status_check', False):
        workflow.add(const.STAGE_FIRST, 'status')
        workflow.add_with_component(const.STAGE_FIRST, 'general', 'status_check')
    workflow.add_with_kwargs(const.STAGE_SECOND, {'option_mode': 'failover_decouple_tenant'}, 'get_relation_tenants', 'get_deployment_connections')
    workflow.add(const.STAGE_SECOND, 'failover_decouple_tenant_pre', 'failover_decouple_tenant')
    workflow.add_with_kwargs(const.STAGE_SECOND, {'delete_password': False}, 'delete_standby_info')
    plugin_context.return_true()
