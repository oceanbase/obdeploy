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


def show_binlog_instances(plugin_context, workflow, *args, **kwargs):
    workflow.add(const.STAGE_FIRST, 'status')
    workflow.add_with_kwargs(const.STAGE_FIRST, {'target_status': ClusterStatus.STATUS_RUNNING, 'fail_exit': True}, 'status_check')
    workflow.add(const.STAGE_FIRST, 'connect')
    if kwargs['component_kwargs'].get('tenant_name'):
        workflow.add_with_kwargs(const.STAGE_FIRST, {"source_option": "show"}, 'target_ob_connect_check', 'tenant_check')
    workflow.add(const.STAGE_FIRST, 'get_binlog_instances')
    return plugin_context.return_true()
