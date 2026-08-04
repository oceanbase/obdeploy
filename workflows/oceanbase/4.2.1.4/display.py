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


def display(plugin_context, workflow, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'status')
    workflow.add_with_component_version_kwargs(const.STAGE_FIRST, 'general', '0.1', {'allow_partial': True}, 'status_check')
    workflow.add_with_kwargs(const.STAGE_SECOND, {'partial_retry_times': 3}, 'connect')
    workflow.add(const.STAGE_SECOND, 'display')
    cluster_config = plugin_context.cluster_config
    component_name = cluster_config.name
    if component_name in [const.COMP_OB_STANDALONE, const.COMP_OB_CE]:
        workflow.add(const.STAGE_SECOND, 'obshell_client')
        workflow.add_with_kwargs(const.STAGE_SECOND, {'skip_when_status_check_failed': True}, 'obshell_health_check', 'obshell_dashboard')
    plugin_context.return_true()
