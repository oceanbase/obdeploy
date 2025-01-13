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


def standby_check(plugin_context, workflow, *args, **kwargs):
    options = plugin_context.options
    workflow.add(const.STAGE_FIRST, 'get_relation_tenants')
    if not getattr(options, 'ignore_standby', False):
        workflow.add(const.STAGE_FIRST, 'get_deployment_connections')
        workflow.add_with_kwargs(const.STAGE_FIRST, {'skip_no_primary_cursor': True}, 'get_standbys')
        workflow.add(const.STAGE_FIRST, 'check_exit_standby')
    plugin_context.return_true()
