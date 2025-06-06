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

def switchover_log_source(plugin_context, workflow, *args, **kwargs):
    options = plugin_context.options
    type = getattr(options, 'type')

    workflow.add(const.STAGE_FIRST, 'obshell_client', 'obshell_health_check')
    workflow.add_with_kwargs(const.STAGE_FIRST, {"version": Version("4.2.4.0"), "comparison_operators": ">="}, 'obshell_version_check')

    workflow.add(const.STAGE_SECOND, 'status')
    workflow.add_with_component(const.STAGE_SECOND, 'general', 'status_check')
    workflow.add_with_kwargs(const.STAGE_SECOND, {'option_mode': 'log_source'}, 'get_relation_tenants', 'get_deployment_connections', 'standby_log_restore_type_check', 'standby_status_check')

    if type == const.SERVICE_MODE:
        workflow.add_with_kwargs(const.STAGE_THIRD, {'option_mode': 'log_source'}, 'create_standbyro', 'dump_standbyro_password')
    else:
        workflow.add_with_kwargs(const.STAGE_THIRD, {'option_mode': 'log_source'}, 'standby_uri_check')
    workflow.add(const.STAGE_FOURTH, 'switchover_log_resource')

    return plugin_context.return_true()