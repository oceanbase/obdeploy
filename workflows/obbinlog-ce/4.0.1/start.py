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
from _deploy import ClusterStatus


def start(plugin_context, workflow, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'parameter_pre')
    if plugin_context.cluster_config.depends:
        ob_repository = kwargs.get("ob_repository")
        binlog_repository = kwargs.get('repository')
        workflow.add_with_component_version_kwargs(const.STAGE_SECOND, ob_repository.name, '4.0.0.0', {'scale_out_component': binlog_repository.name}, 'connect', 'create_tenant', 'create_user', 'import_time_zone')
    else:
        workflow.add(const.STAGE_SECOND, 'cursor_check')
    workflow.add(const.STAGE_THIRD, 'init_schema', 'start', 'health_check', 'connect')
    workflow.add(const.STAGE_THIRD, 'status')
    workflow.add_with_kwargs(const.STAGE_THIRD, {'target_status': ClusterStatus.STATUS_RUNNING}, 'status_check')
    workflow.add_with_kwargs(const.STAGE_THIRD, {'show_result': False}, 'get_binlog_instances')
    workflow.add_with_kwargs(const.STAGE_THIRD, {'source_option': 'start', 'no_instance_exit': False}, 'instance_manager')
    return plugin_context.return_true()
