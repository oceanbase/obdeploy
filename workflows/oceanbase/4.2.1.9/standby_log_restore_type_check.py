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

def standby_log_restore_type_check(plugin_context, workflow, *args, **kwargs):
    options = plugin_context.options
    workflow.add(const.STAGE_FIRST, 'obshell_client', 'obshell_health_check')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"version": Version("4.2.4.0"), "comparison_operators": ">="}, 'obshell_version_check')

    if not getattr(options, 'skip_cluster_status_check', False):
        workflow.add(const.STAGE_SECOND, 'status')
        workflow.add_with_component(const.STAGE_SECOND, 'general', 'status_check')

    workflow.add_with_kwargs(const.STAGE_THIRD, {'option_mode': 'switchover_tenant'}, 'get_relation_tenants', 'get_deployment_connections', 'standby_log_restore_type_check')
    return plugin_context.return_true()