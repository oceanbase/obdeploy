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


def create_standby_tenant(plugin_context, workflow, *args, **kwargs):
    options = plugin_context.options
    if not getattr(options, 'skip_cluster_status_check', False):
        workflow.add(const.STAGE_FIRST, 'status')
        workflow.add_with_component(const.STAGE_FIRST, 'general', 'status_check')
    workflow.add_with_kwargs(const.STAGE_SECOND, {'option_mode': 'create_standby_tenant'}, 'get_relation_tenants', 'get_deployment_connections')
    workflow.add(const.STAGE_SECOND, 'create_standby_tenant_pre', 'create_standby_tenant')
    plugin_context.return_true()
