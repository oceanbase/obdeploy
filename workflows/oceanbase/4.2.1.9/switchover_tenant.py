# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

import const
from _rpm import Version


def switchover_tenant(plugin_context, workflow, *args, **kwargs):
    log_source_type = plugin_context.get_variable('source_type')
    if log_source_type == const.LOCATION_MODE:
        workflow.add(const.STAGE_FIRST, 'obshell_client', 'obshell_health_check')
        workflow.add_with_kwargs(const.STAGE_FIRST, {"version": Version("4.2.4.0"), "comparison_operators": ">="}, 'obshell_version_check')

        workflow.add_with_kwargs(const.STAGE_SECOND, {'source_type': log_source_type, 'option_mode': 'switchover'}, 'standby_uri_check', 'switchover_tenant_pre')
        workflow.add(const.STAGE_SECOND, 'standby_status_check', 'switchover_location_tenant')
    else:
        workflow.add_with_kwargs(const.STAGE_SECOND, {'option_mode': 'switchover'}, 'standby_uri_check')
        workflow.add(const.STAGE_SECOND, 'switchover_tenant_pre', 'switchover_tenant')
    workflow.add(const.STAGE_THIRD, 'switchover_relation_tenants', 'switchover_primary_tenant_info')
    plugin_context.return_true()
